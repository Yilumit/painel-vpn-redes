#!/usr/bin/python3

import os
import subprocess
import sys
import shutil
from dotenv import load_dotenv

EASYRSA_DIR = "/usr/share/easy-rsa"
CRL_PATH = os.path.join(EASYRSA_DIR, "pki", "crl.pem")
OPENVPN_DIR = "/etc/openvpn/"

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

def revoke_cert(client_name, cert_name):
    """
    Revoga um certificado de cliente OpenVPN, gera uma nova CRL e remove os arquivos associados ao certificado.

    Parametros:
        client_name (str): Nome do cliente associado ao certificado a ser revogado.
        cert_name (str): Nome do certificado que sera revogado.

    Excecoes:
        Falhas na copia do CRL ou remocao de arquivos são exibidas no console, mas não impedem a execucao.
    """
    
    os.environ["EASYRSA_BATCH"] = "1"
    os.environ["EASYRSA_REQ_CN"] = cert_name

    run_easyrsa_command(["revoke", cert_name], f"Revogando certificado {cert_name}", env_easyrsa_pass=True)
    run_easyrsa_command(["gen-crl"], "Gerando nova CRL")

    try:
        #server.conf aponta para este caminho para verificar a CRL
        dest_crl = os.path.join(OPENVPN_DIR, "crl.pem")
        shutil.copyfile(CRL_PATH, dest_crl)
        os.chmod(dest_crl, 0o640)
    except Exception as e:
        print(f"Erro ao copiar CRL para {dest_crl}: {e}")
        
    paths_to_remove = [
        os.path.join(EASYRSA_DIR, "pki", "issued", f"{cert_name}.crt"),
        os.path.join(EASYRSA_DIR, "pki", "private", f"{cert_name}.key"),
        f"{OPENVPN_DIR}/client/{client_name}/{cert_name}/",
        os.path.join(OPENVPN_DIR, "client", client_name, f"{cert_name}.zip")
    ]

    for path in paths_to_remove:
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                print(f"Erro ao remover {path}: {e}")
                continue
        elif not path.endswith((".crt", ".key")):
            print(f"{path} não encontrado!")

    print(f"Certificado '{cert_name}' revogado.")
    sys.e

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Use: revoke_vpn_client.py <client_name> <cert_name>")
        sys.exit(1)

    client_name = sys.argv[1]
    cert_name = sys.argv[2]
    revoke_cert(client_name=client_name, cert_name=cert_name)
