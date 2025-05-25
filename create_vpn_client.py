#!/usr/bin/python3

import os
import sys
import subprocess
import psycopg2 as pg
from dotenv import load_dotenv
from uuid import uuid4


EASYRSA_DIR = "/usr/share/easy-rsa"
OUTPUT_DIR = "/etc/openvpn/client"

load_dotenv(dotenv_path="/etc/openvpn/.env")

def run_easyrsa_command(args, description, env_easyrsa_pass=False):
    """
    Executa os comandos no diretorio do easy-rsa com seguranca.

    parametros:
        args (list[strg]): Lista de argumentos do comando que sera passado para o script './easyrsa'.
        description (str): Descricaoo da etapa, usada apenas para log e depuracao.
        env_easyrsa_pass (bool): Se True, inclui EASYRSA_PASSIN no ambiente.

    Excecoes:
        subprocess.CalledProcessError: Caso a execucao do comando resulte em erro, o script sera interrompido.
    """
    print(f"{description}: {' '.join(args)}")
    try:
        env = os.environ.copy()
        if env_easyrsa_pass:
            env["EASYRSA_PASSIN"] = os.getenv("EASYRSA_PASSIN")
        subprocess.run(["./easyrsa"] + args, cwd=EASYRSA_DIR, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro '{description}': {e}")
        sys.exit(1)

def generate_ovpn_file(client_dir, cert_random):
    """
    Gera o arquivo de configuracao do cliente com as informacoes necessarias para se conectar 
    com seguranca ao servidor VPN.

    parametros:
        client_name (str): Nome do cliente VPN.
        client_dir (str): Caminho do diretorio onde os arquivos da VPN do cliente estao armazenados.
        cert_random (str): Nome aleatorio do cliente, usado para diferenciar os arquivos.
    """
    ovpn_path = os.path.join(client_dir, f"{cert_random}.ovpn")

    with open(ovpn_path, "w") as f:
        f.write(f"""client
dev tun
proto udp

# Tem que colocar na linha abaixo o IP acessivel do SERVIDOR COM OPENVPN
remote <10.68.76.250> 1194

ca ca.crt
cert {cert_random}.crt
key {cert_random}.key

tls-client
resolv-retry infinite
nobind
persist-key
persist-tun
""")


def create_and_sign_client_cert(client_name):
    """
    Gera e assina um certificado OpenVPN para um cliente utilizando Easy RSA.

    Parametros:
        client_name (str): Nome do usuario solicitando acesso a VPN.

    Excecoes:
        Encerra a execucao se o nome do cliente estiver vazio.
    """
    if not client_name:
        print("Erro: Nome do usuário é obrigatório.")
        sys.exit(1)

    cert_random = str(uuid4())[:20]
    
    #Ativa o modo nao interativo do Easy-RSA
    os.environ["EASYRSA_BATCH"] = "1"
    os.environ["EASYRSA_REQ_CN"] = cert_random

    # Gerar par de chaves e requisacao de assinatura de cert
    run_easyrsa_command(["gen-req", cert_random, "nopass"], f"Gerarando CSR para {client_name}")
    # Assinar a requisicao com a CA (autoridade certificadora)
    run_easyrsa_command(["sign-req", "client", cert_random], f"Assinando certificado de {client_name}", env_easyrsa_pass=True)

    client_dir = os.path.join(OUTPUT_DIR, client_name, cert_random)
    os.makedirs(client_dir, exist_ok=True)

    files_to_copy = {
        f"{EASYRSA_DIR}/pki/issued/{cert_random}.crt": f"{client_dir}/{cert_random}.crt",
        f"{EASYRSA_DIR}/pki/private/{cert_random}.key": f"{client_dir}/{cert_random}.key",
        f"{EASYRSA_DIR}/pki/ca.crt": f"{client_dir}/ca.crt"
    }

    for src, dest in files_to_copy.items():
        if not os.path.exists(src):
            print(f"Arquivo não encontrado: {src}")
            continue
        subprocess.run(["cp", src, dest])

    generate_ovpn_file(client_dir, cert_random)

    print(f"Certificado do cliente '{client_name}' criado e assinado com sucesso.")

    return cert_random, client_dir

def insert_into_database(id, name_cert, path):
    """
    Insere o caminho do certificado no banco de dados.

    Parametros:
        id (int): ID do cliente.
        name_cert (str): Nome do certificado do cliente.
        path (str): Caminho do diretorio onde os arquivos do cliente estao armazenados.
    """
    connection = None   
    try:
        database_name = os.getenv("DATABASE_NAME")
        connection = pg.connect(
            dbname=database_name,
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASS"),
            host=os.getenv("DATABASE_HOST"),
            port=os.getenv("DATABASE_PORT")
        )
        cursor = connection.cursor()
        cursor.execute(f"""
            INSERT INTO {database_name}.certificados_vpn (funcionario_id, nome_certificado, caminho_arquivos)
            VALUES ({id}, '{name_cert}', '{path}')
        """)
        connection.commit()
    except pg.Error as e:
        print(f"Erro ao inserir no banco de dados: {e}")

    finally:
        if connection:
            cursor.close()
            connection.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(1)

    client = sys.argv[1]
    id_client = int(sys.argv[2])

    name_cert, path = create_and_sign_client_cert(client)
    insert_into_database(id_client, name_cert, path) 
