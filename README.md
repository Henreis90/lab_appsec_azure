# Infraestrutura Azure PostgreSQL em Terraform (Custo Mínimo)

Projeto Terraform para provisionamento de banco de dados relacional **PostgreSQL Flexible Server** na Azure com foco em menor custo e boas práticas de segurança para estudo de aplicações.

---

## 🛠️ Pré-requisitos

1. **Azure CLI** instalado e autenticado (`az login --tenant e5d851ea-6a65-44c3-8050-fba3af02e6ad`)
2. **Terraform CLI** instalado (v1.3+)
3. Docker
4. Conta ativa na Azure

---

## 🚀 Como Executar

### 1. Clonar e Inicializar
```bash
git clone <seu-repositorio>
cd terraform
terraform init
```
<img width="1110" height="546" alt="image" src="https://github.com/user-attachments/assets/3af29034-5e11-40b6-88d2-89eac34aab42" />

Aqui está a lista completa de todas as rotas e métodos disponíveis na sua API com base no código desenvolvido:

| Método | Endpoint | Descrição / Ação | Exemplo de Uso (curl) |
| --- | --- | --- | --- |
| **GET** | `/` | Verifica o status da API (health check). | `curl http://localhost:8080/` |
| **GET** | `/items` | Lista todos os itens cadastrados no banco de dados. | `curl http://localhost:8080/items` |
| **POST** | `/items` | Cria/insere um novo item no banco de dados. | `curl -X POST http://localhost:8080/items -H "Content-Type: application/json" -d '{"name": "Item 1", "description": "Teste"}'` |
| **DELETE** | `/items/<id>` | Deleta um item específico com base no ID informado. | `curl -X DELETE http://localhost:8080/items/1` |
