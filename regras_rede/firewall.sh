#!/bin/bash

# Limpa todas as regras anteriores
nft flush ruleset

# Criacao das tabelas
nft add table inat filter
nft add table ip nat

# Chains da tabela filter com políticas padrao
nft add chain inat filter input   { type filter hook input priority 0 \; policy drop \; }
nft add chain inat filter forward { type filter hook forward priority 0 \; policy drop \; }
nft add chain inat filter output  { type filter hook output priority 0 \; policy accept \; }

# Chains da tabela nat para redirecionamento e mascaramento
nft add chain ip nat prerouting  { type nat hook prerouting priority -100 \; }
nft add chain ip nat postrouting { type nat hook postrouting priority 100 \; }

# -----------------------------
# Permissoes Basicas
# -----------------------------

# Permitir trafego local (loopback)
nft add rule inat filter input iif lo accept

# Permitir pacotes relacionados a conexoes estabelecidas
nft add rule inat filter input ct state established,related accept
nft add rule inat filter forward ct state established,related accept

# -----------------------------
# Comunicacao Rede Interna (CRITICO!)
# -----------------------------

# Permitir comunicação entre VMs da rede interna
nft add rule ip filter forward iif enp0s8 oif enp0s8 ip saddr 192.168.200.0/24 ip daddr 192.168.200.0/24 accept

# -----------------------------
# Redirecionamentos NAT
# -----------------------------

# Redirecionar HTTP (porta 80) para HTTPS (porta 443) no container WEB
nft add rule ip nat prerouting iif enp0s3 tcp dport 80 dnat to 192.168.200.2:443
nft add rule inat filter forward iif enp0s3 ip daddr 192.168.200.2 tcp dport 443 accept

# Redirecionamento direto HTTPS para o container WEB
nft add rule ip nat prerouting iif enp0s3 tcp dport 443 dnat to 192.168.200.2:443
nft add rule inat filter forward iif enp0s3 ip daddr 192.168.200.2 tcp dport 443 accept

# Redirecionar trafego OpenVPN (UDP 1194) para o OpenVPN
nft add rule ip nat prerouting iif enp0s3 udp dport 1194 dnat to 192.168.200.2:1194
nft add rule inat filter forward iif enp0s3 ip daddr 192.168.200.2 udp dport 1194 accept

# -----------------------------
# Restrições de Acesso
# -----------------------------

# Permitir SSH (porta 22) apenas da rede interna
nft add rule inat filter input iif enp0s8 ip saddr 192.168.200.0/24 tcp dport 22 accept

# Bloquear qualquer outro trafego vindo da Internet para a rede interna
nft add rule inat filter forward iif enp0s3 ip daddr 192.168.200.0/24 drop

# -----------------------------
# NAT de Saída
# -----------------------------

# Permitir que clientes da rede interna acessem a internet
nft add rule ip nat postrouting oif enp0s3 ip saddr 192.168.200.0/24 masquerade