#!/usr/bin/python3

import os
import sys
import subprocess

EASYRSA_DIR = "/usr/share/easy-rsa"
OUTPUT_DIR = "/etc/openvpn/client"

def run_easyrsa_command(args, description):
    """
    Executa os comandos no diretorio do easy-rsa com seguranca.

    parametros:
        args (list[strg]): Lista de argumentos do comando que sera passado para o script './easyrsa'.
        description (str): Descrição da etapa, usada apenas para log e depuracao.

    Excecoes:
        subprocess.CalledProcessError: Caso a execucao do comando resulte em erro, o script sera interrompido.

    """
    print(f"> {description}: {' '.join(args)}")
    try:
        #Navega ate o diretorio com cwd ao executar
        subprocess.run(["./easyrsa"] + args, cwd=EASYRSA_DIR, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro ao '{description}': {e}")
        sys.exit(1)

def generate_ovpn_file(client_name, client_dir):
    """
    Gera o arquivo de configuracao do cliente com as informacoes necessarias para se conectar 
    com seguranca ao servidor VPN.

    parametros:
        client_name (str): Nome do cliente VPN.
        client_dir (str): Caminho do diretorio onde os arquivos da VPN do cliente estao armazenados.

    Saida:
        Um arquivo '<cliente>.ovpn' criado no diretorio especificado.
    """
    ovpn_path = os.path.join(client_dir, f"{client_name}.ovpn")

    with open(ovpn_path, "w") as f:
        f.write(f"""client
dev tun
proto udp

# Tem que colocar na linha abaixo o IP acessivel do SERVIDOR COM OPENVPN
remote <192.168.0.16> 1194

ca ca.crt
cert {client_name}.crt
key {client_name}.key

tls-client
resolv-retry infinite
nobind
persist-key
persist-tun
""")
    print(f"Arquivo .ovpn gerado: {ovpn_path}")

def create_and_sign_client_cert(client_name):
    """
    Gera e assina um certificado OpenVPN para um cliente utilizando Easy RSA.

    Parametros:
        client_name (str): Nome do cliente VPN. Sera usado como Common Name (CN).

    Excecoes:
        Encerra a execucao se o nome do cliente estiver vazio.
    """
    if not client_name:
        print("Erro: Nome do cliente é obrigatório.")
        sys.exit(1)

    #Ativa o modo nao interativo do Easy-RSA
    os.environ["EASYRSA_BATCH"] = "1"
    #Define o Common Name automaticamente 
    os.environ["EASYRSA_REQ_CN"] = client_name

    # Gerar par de chaves e requisacao de assinatura de cert
    run_easyrsa_command(["gen-req", client_name, "nopass"], f"Gerar CSR para {client_name}")

    # Assinar a requisicao com a CA (autoridade certificadora)
    run_easyrsa_command(["sign-req", "client", client_name], f"Assinar certificado de {client_name}")

    # Juntar os arquivos
    client_dir = os.path.join(OUTPUT_DIR, client_name)
    os.makedirs(client_dir, exist_ok=True)

    files_to_copy = {
        f"{EASYRSA_DIR}/pki/issued/{client_name}.crt": f"{client_dir}/{client_name}.crt",
        f"{EASYRSA_DIR}/pki/private/{client_name}.key": f"{client_dir}/{client_name}.key",
        f"{EASYRSA_DIR}/pki/ca.crt": f"{client_dir}/ca.crt"
    }

    for src, dest in files_to_copy.items():
        if not os.path.exists(src):
            print(f"Arquivo não encontrado: {src}")
            continue
        subprocess.run(["cp", src, dest])

    print(f"Certificado do cliente '{client_name}' criado e assinado com sucesso.")
    print(f"Arquivos disponíveis em: {client_dir}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Use: sudo python3 create_vpn_user.py <nome_do_cliente>")
        sys.exit(1)

    client = sys.argv[1]
    create_and_sign_client_cert(client)
