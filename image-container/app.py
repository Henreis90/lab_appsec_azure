import os
from flask import Flask, jsonify, request
import pymssql

app = Flask(__name__)

# Configurações do Banco pegas via Variáveis de Ambiente
DB_SERVER = os.environ.get("DB_SERVER", "localhost")
DB_USER = os.environ.get("DB_USER", "sqladmin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "sua_senha")
DB_NAME = os.environ.get("DB_NAME", "appdb")


def get_db_connection():
  return pymssql.connect(
      server=DB_SERVER, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
  )


# Inicializa a tabela de teste se não existir
@app.before_first_request
def init_db():
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
  except Exception as e:
    print(f"Erro ao conectar/criar tabela no banco: {e}")


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
