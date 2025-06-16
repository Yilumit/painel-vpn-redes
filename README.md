# Painel VPN Redes

Este repositório contém scripts e regras de firewall para gerenciamento de clientes OpenVPN e controle de tráfego em uma rede segmentada, composta por três máquinas principais:

- **Servidor OpenVPN**: Responsável pela autenticação e conexão dos clientes VPN. Além de executar a aplicação Painel VPN para gerar e gerenciar os certificados VPN de funcionários.
- **Firewall**: Controla o tráfego entre as redes, aplica NAT e redirecionamentos.
- **Servidor de Banco de Dados**: Dedicado ao armazenamento das informações da aplicação de gerenciamento de certificados VPN. 

---

## Scripts Python

Os scripts localizados em `scripts/` são utilizados para gerenciar certificados de clientes OpenVPN:

### 1. `create_vpn_client.py`

- **Função:** Cria e assina um certificado para um novo cliente VPN.
- **Como funciona:**
  - É invocado pela aplicação Painel VPN.
  - Gera um par de chaves e um certificado usando o EasyRSA.
  - Assina o certificado com a CA (Autoridade Certificadora).
  - Copia os arquivos necessários para um diretório específico do cliente.
  - Gera um arquivo `.ovpn` de configuração para o cliente, já apontando para o IP do servidor OpenVPN com uma função que pega o ip da máquina que está rodando o script.
  - Compacta todos os arquivos do cliente em um `.zip` para facilitar o envio.
- **Uso:**
  ```
  ./create_vpn_client.py <nome_do_cliente>
  ```

### 2. `revoke_vpn_client.py`

- **Função:** Revoga o certificado de um cliente VPN.
- **Como funciona:**
  - Revoga o certificado do cliente usando o EasyRSA.
  - Gera uma nova CRL (lista de certificados revogados).
  - Remove os arquivos do certificado e configurações do cliente do servidor.
- **Uso:**
  ```
  ./revoke_vpn_client.py <nome_do_cliente> <nome_do_certificado>
  ```

> **Observação:** Ambos os scripts utilizam variáveis de ambiente definidas no arquivo `.env` para acessar senhas e configurações sensíveis, o arquivo `.env` deve estar localizado no caminho: `/etc/openvpn/.env` ou deve ser alterado nos scripts para o caminho desejado.

---

## Regras de Firewall

O script `regras_rede/firewall.sh` utiliza o `nftables` para definir as regras de firewall e NAT. Ele deve ser executado na máquina Firewall.

### Principais regras e funções:

- **Limpeza e criação de tabelas:** Remove regras antigas e cria novas tabelas para filtragem e NAT.
- **Permissões básicas:**
  - Permite tráfego local (loopback).
  - Permite pacotes relacionados a conexões já estabelecidas.
- **Comunicação interna:** Permite comunicação entre máquinas da rede interna (ex: OpenVPN, Banco de Dados).
- **Redirecionamentos NAT:**
  - Redireciona tráfego HTTP (porta 80) e HTTPS (porta 443) da interface externa para o servidor web interno.
  - Redireciona tráfego UDP na porta 1194 (OpenVPN) para o servidor OpenVPN.
- **Restrições de acesso:**
  - Permite SSH apenas a partir da rede interna.
  - Bloqueia qualquer tráfego vindo da internet para a rede interna, exceto o explicitamente permitido.
- **NAT de saída:** Permite que clientes da rede interna acessem a internet através de mascaramento.

### Exemplo de fluxo:

1. **Cliente externo** acessa o IP público da Firewall na porta 1194/UDP e o Firewall redireciona para o servidor OpenVPN que está na rede interna. O servidor aceitará apenas os clientes com certificado OpenVPN.
2. **Cliente VPN** conecta na aplicação, recebe configuração e certificado criado pelos scripts Python.
3. **Acesso ao Banco de Dados** é restrito à rede interna, protegendo o servidor de banco de dados de acessos externos.

---

## Estrutura do Projeto

```
painel-vpn-redes/
  .env
  README.md
  regras_rede/
    firewall.sh
  scripts/
    create_vpn_client.py
    revoke_vpn_client.py
```

---

## Observações

- Certifique-se de que o EasyRSA está instalado no servidor OpenVPN e **configurado** corretamente.
- O arquivo `.env` deve conter as variáveis de ambiente necessárias para os scripts Python.
- O script de firewall deve ser executado com privilégios de superusuário na máquina Firewall, ou deve ser criado um serviço para executar esse script a cada inicialização da máquina.
- O servidor de banco de dados deve estar acessível apenas pela rede interna para maior segurança.