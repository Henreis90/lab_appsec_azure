# Enterprise Security Laboratory (Lab AppSec)

Laboratório de infraestrutura e arquitetura de segurança voltado para ambientes corporativos (Enterprise). O projeto demonstra a implementação de uma aplicação conteinerizada segura utilizando segregação de redes, autenticação centralizada OIDC com validação de tokens RS256/JWKS, gestão de segredos e persistência relacional.

---

## 🏗️ Arquitetura e Topologia de Rede

Para garantir o isolamento adequado e seguir as boas práticas de segurança defensiva, o laboratório é dividido em duas redes Docker distintas:

1. **`dmz-net` (Zona Desmilitarizada):** 
   - Contém o **Nginx Gateway**, que atua como o ponto único de entrada (Reverse Proxy), direcionando o tráfego externo de forma controlada para os serviços internos.
2. **`internal-net` (Rede Interna Isolada):** 
   - Abriga os serviços críticos que não devem ser expostos diretamente à internet: **Flask API**, **Keycloak**, **HashiCorp Vault** e **SQL Server**.

---

## 🛠️ Stack Tecnológica

- **Proxy Reverso & Gateway:** Nginx
- **Aplicação / API:** Python (Flask) protegido com decorators de autenticação (`@token_required`)
- **Provedor de Identidade (IdP):** Keycloak 24 (OIDC, OAuth2, RS256, JWKS)
- **Gestão de Segredos:** HashiCorp Vault
- **Banco de Dados:** Microsoft SQL Server (Enterprise)
- **Orquestração:** Docker & Docker Compose

---

## 🚀 Como Executar o Laboratório

### 1. Pré-requisitos
- Docker e Docker Compose instalados na máquina (ou VM Linux).

### 2. Clonar o Repositório e Configurar o Ambiente
Certifique-se de preencher as variáveis de ambiente necessárias nos arquivos de configuração ou no `.env` conforme o modelo do projeto.

### 3. Subir os Containers
Execute o comando abaixo para iniciar todos os serviços definidos no Docker Compose em segundo plano:

```bash
docker compose up -d --build

🔐 Configuração do Keycloak e Autenticação
O Keycloak é o componente responsável pela gestão de identidades e emissão de tokens JWT.

Criar e Configurar o Administrador
Caso o bootstrap não crie o usuário admin automaticamente via variáveis de ambiente (KEYCLOAK_ADMIN), você pode configurá-lo e validá-lo via CLI no container:

Bash
docker exec -it keycloak_lab /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password <SUA_SENHA_ADMIN>
🧪 Testando a API e o Fluxo de Segurança
O fluxo padrão exige a obtenção de um token de acesso OIDC válido para consumir os endpoints protegidos da API Flask.

1. Obter o Token JWT (Exemplo com o usuário de teste)
Bash
TOKEN=$(curl -s -X POST "http://localhost:9080/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli" \
  -d "username=joao" \
  -d "password=<SENHA_DO_USUARIO>" \
  -d "grant_type=password" | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')
2. Consumir a Rota Protegida (GET)
Bash
curl -X GET http://localhost:8080/items \
  -H "Authorization: Bearer $TOKEN"
3. Criar um Novo Registro no Banco (POST)
Bash
curl -X POST http://localhost:8080/items \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Servidor Lab AppSec", "descricao": "Laboratório de isolamento e Keycloak"}'
🛡️ Segurança Aplicada
Zero Hardcoded Secrets: Credenciais sensíveis e senhas de banco são injetadas via variáveis de ambiente seguras e gerenciadas por cofre.

Validação Criptográfica: A API valida a assinatura dos tokens JWT em tempo de execução utilizando as chaves públicas JWKS fornecidas pelo Keycloak.

Isolamento Perimétrico: Apenas o Nginx expõe portas para o mundo externo; os demais serviços comunicam-se exclusivamente dentro da rede interna do Docker.

<img width="1337" height="625" alt="image" src="https://github.com/user-attachments/assets/7429d56b-66f5-4364-87bb-1f461296c7ed" />


Aqui está a lista completa de todas as rotas e métodos disponíveis na sua API com base no código desenvolvido:

| Método | Endpoint | Descrição / Ação | Exemplo de Uso (curl) |
| --- | --- | --- | --- |
| **GET** | `/` | Verifica o status da API (health check). | `curl http://localhost:8080/` |
| **GET** | `/items` | Lista todos os itens cadastrados no banco de dados. | `curl http://localhost:8080/items` |
| **POST** | `/items` | Cria/insere um novo item no banco de dados. | `curl -X POST http://localhost:8080/items -H "Content-Type: application/json" -d '{"name": "Item 1", "description": "Teste"}'` |
| **DELETE** | `/items/<id>` | Deleta um item específico com base no ID informado. | `curl -X DELETE http://localhost:8080/items/1` |
