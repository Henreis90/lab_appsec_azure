import os
import time
from flask import Flask, jsonify, request
import hvac
import pymssql

app = Flask(__name__)

# Configurações do Vault e do Servidor pegas via Variáveis de Ambiente
VAULT_URL = os.environ.get("VAULT_URL", "http://vault:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "root-token-seguro")
DB_SERVER = os.environ.get("DB_SERVER", "db")
DB_NAME = os.environ.get("DB_NAME", "appdb")


def get_db_credentials_from_vault():
  """Busca as credenciais do banco de dados dinamicamente no HashiCorp Vault."""
  try:
    client = hvac.Client(url=VAULT_URL, token=VAULT_TOKEN)

    # Lê o segredo do caminho 'secret/data/db' (KV Versão 2)
    secret_response = client.secrets.kv.v2.read_secret_version(
        mount_point="secret", path="db"
    )

    db_user = secret_response["data"]["data"]["user"]
    db_pass = secret_response["data"]["data"]["password"]
    return db_user, db_pass
  except Exception as e:
    print(f"Erro ao buscar credenciais no Vault: {e}")
    # Fallback opcional caso queira seguranca local de emergencia, ou lance a excecao
    raise e


def get_db_connection():
  # Pega as credenciais atualizadas do Vault a cada nova conexão (ou você pode cachear se preferir)
  db_user, db_pass = get_db_credentials_from_vault()
  return pymssql.connect(
      server=DB_SERVER, user=db_user, password=db_pass, database=DB_NAME
  )


# Loop de tentativas para aguardar o SQL Server subir
print("Aguardando o SQL Server ficar pronto...")
connected = False
attempts = 15  # Tenta por até 45 segundos (15 * 3s)

while attempts > 0 and not connected:
  try:
    # Para validar a conexão inicial e criar o banco, precisamos das credenciais do Vault
    db_user, db_pass = get_db_credentials_from_vault()

    conn_master = pymssql.connect(
        server=DB_SERVER, user=db_user, password=db_pass, database="master"
    )
    conn_master.autocommit(True)
    cursor_master = conn_master.cursor()
    cursor_master.execute(f"""
            IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{DB_NAME}')
            CREATE DATABASE {DB_NAME}
        """)
    conn_master.close()
    connected = True
    print("Conectado ao SQL Server e credenciais validadas via Vault!")
  except Exception as e:
    print(
        f"Banco/Vault ainda iniciando... Tentativas restantes: {attempts}."
        f" Erro: {e}"
    )
    time.sleep(3)
    attempts -= 1

if not connected:
  print("ERRO: Não foi possível conectar ao SQL Server após várias tentativas.")

# Inicializa a tabela caso tenha conectado
if connected:
  try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='items' and xtype='U')
            CREATE TABLE items (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description VARCHAR(255)
            )
        """)
    conn.commit()
    conn.close()
    print("Tabela 'items' verificada/criada com sucesso!")
  except Exception as e:
    print(f"Erro ao criar tabela: {e}")


@app.route("/", methods=["GET"])
def home():
  return jsonify({"status": "API AppSec Lab rodando com sucesso!"})


# GET: Listar todos os itens
@app.route("/items", methods=["GET"])
def get_items():
  try:
    conn = get_db_connection()
    cursor = conn.cursor(as_dict=True)
    cursor.execute("SELECT id, name, description FROM items")
    items = cursor.fetchall()
    conn.close()
    return jsonify(items), 200
  except Exception as e:
    return jsonify({"error": str(e)}), 500


# POST: Criar um item
@app.route("/items", methods=["POST"])
def create_item():
  data = request.json
  name = data.get("name")
  description = data.get("description", "")

  if not name:
    return jsonify({"error": "O campo 'name' é obrigatório"}), 400

  try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (name, description) VALUES (%s, %s)",
        (name, description),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Item criado com sucesso!"}), 201
  except Exception as e:
    return jsonify({"error": str(e)}), 500


# DELETE: Deletar um item por ID
@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
  try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Item {item_id} deletado com sucesso!"}), 200
  except Exception as e:
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=80)
