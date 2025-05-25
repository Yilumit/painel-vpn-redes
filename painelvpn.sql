CREATE SCHEMA IF NOT EXISTS painelvpn AUTHORIZATION vpnuser;
SET search_path TO painelvpn;

create table funcionarios (
    id SERIAL,
    nome VARCHAR(50) NOT NULL,
    usuario VARCHAR(50) NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    email varchar(50) NOT NULL UNIQUE,
    criado_em TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE administradores (
    funcionario_id SERIAL
);

CREATE TABLE certificados_vpn (
    id SERIAL,
    funcionario_id INT NOT NULL,
    nome_certificado VARCHAR(100) NOT NULL,
    caminho_arquivos TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT current_timestamp
);

-- PK --
ALTER TABLE funcionarios
    ADD CONSTRAINT pk_func PRIMARY KEY (id),
    ADD CONSTRAINT uq_func_email UNIQUE (email),
    ADD CONSTRAINT uq_func_usuario UNIQUE (usuario);
ALTER TABLE administradores
    ADD CONSTRAINT pk_adm PRIMARY KEY (funcionario_id);
ALTER TABLE certificados_vpn
    ADD CONSTRAINT pk_cert PRIMARY KEY (id);

-- FK --
ALTER TABLE administradores
    ADD CONSTRAINT fk_adm_func FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id),
    ON DELETE CASCADE;
ALTER TABLE certificados_vpn
    ADD CONSTRAINT fk_cert_func FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id)
    ON DELETE CASCADE;

