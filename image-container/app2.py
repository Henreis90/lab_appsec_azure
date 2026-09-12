import os
import time
from flask import Flask, jsonify, request
import pymssql

app = Flask(__name__)

# Configurações do Banco pegas via Variáveis de Ambiente
DB_SERVER = os.environ.get("DB_SERVER", "db")
DB_USER = os.environ.get("DB_USER", "sa")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "PasswordAppSec123!")
DB_NAME = os.environ.get("DB_NAME", "appdb")

def get_db_connection():
  return pymssql.connect(
      server=DB_SERVER, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
  )

# Loop de tentativas para aguardar o SQL Server subir
print("Aguardando o SQL Server ficar pronto...")
connected = False
attempts = 15  # Tenta por até 45 segundos (15 * 3s)

while attempts > 0 and not connected:
  try:
    conn_master = pymssql.connect(
        server=DB_SERVER, user=DB_USER, password=DB_PASSWORD, database="master"
    )
    conn_master.autocommit(True)
    cursor_master = conn_master.cursor()
    cursor_master.execute(f"""
            IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{DB_NAME}')
            CREATE DATABASE {DB_NAME}
        """)
    conn_master.close()
    connected = True
    print("Conectado ao SQL Server com sucesso!")
  except Exception as e:
    print(f"Banco ainda iniciando... Tentativas restantes: {attempts}. Erro: {e}")
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
