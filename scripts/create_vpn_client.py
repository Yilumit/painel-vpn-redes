#!/usr/bin/python3

import os
import sys
import subprocess
import zipfile
import socket
from dotenv import load_dotenv
from uuid import uuid4


EASYRSA_DIR = "/usr/share/easy-rsa"
OUTPUT_DIR = "/etc/openvpn/client"

load_dotenv(dotenv_path="/etc/openvpn/.env")

def get_ip():
    """
    Obtem o IPV4 da interface de rede usada para acessar a internet.

    Retorna:
        str: O endereço IP local da maquina.

    Excecoes:
        RuntimeError: Se houver erro ao determinar o IP, uma excecao com mensagem descritiva e lancada.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    except Exception as e:
        raise RuntimeError(f"Falha ao determinar o IP: {e}")

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
    # print(f"{description}: {' '.join(args)}")
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

    ip = get_ip()

    with open(ovpn_path, "w") as f:
        f.write(f"""client
dev tun
proto udp

# Tem que colocar na linha abaixo o IP acessivel do SERVIDOR COM OPENVPN
remote {ip} 1194

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
    """
    cert_random = str(uuid4())[:7]
    
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
        f"{EASYRSA_DIR}/pki/dh.pem": f"{client_dir}/dh.pem",
        f"{EASYRSA_DIR}/pki/ca.crt": f"{client_dir}/ca.crt"
    }

    for src, dest in files_to_copy.items():
        if not os.path.exists(src):
            # print(f"Arquivo não encontrado: {src}")
            continue
        subprocess.run(["cp", src, dest])

    generate_ovpn_file(client_dir, cert_random)
    # print(f"Certificado do cliente '{client_name}' criado e assinado com sucesso.")

    with zipfile.ZipFile(f"{client_dir}.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(client_dir):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=os.path.join(cert_random, file))

    print(cert_random)
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Use: create_vpn_client.py <client_name>")
        sys.exit(1)

    client = sys.argv[1]
    create_and_sign_client_cert(client)
