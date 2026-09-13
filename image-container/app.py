import json
import os
from functools import wraps
from flask import Flask, jsonify, request
import hvac
import jwt  # Biblioteca PyJWT
#import pymssql
import requests
import pyodbc

app = Flask(__name__)

# URL interna onde o Keycloak expõe as chaves públicas (JWKS)
# Usamos o realm padrão 'master' para simplificar o lab
KEYCLOAK_JWKS_URL = "http://keycloak:8080/realms/master/protocol/openid-connect/certs"

# Configurações do Vault e do Servidor
VAULT_URL = os.environ.get("VAULT_URL", "http://vault:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "root-token-seguro")
DB_SERVER = os.environ.get("DB_SERVER", "db")
DB_NAME = os.environ.get("DB_NAME", "appdb")


def get_db_credentials_from_vault():
  try:
    client = hvac.Client(url=VAULT_URL, token=VAULT_TOKEN)
    secret_response = client.secrets.kv.v2.read_secret_version(
        mount_point="secret", path="db"
    )
    return (
        secret_response["data"]["data"]["user"],
        secret_response["data"]["data"]["password"],
    )
  except Exception as e:
    raise e


#def get_db_connection():
#  db_user, db_pass = get_db_credentials_from_vault()
#  return pymssql.connect(
#      server=DB_SERVER, user=db_user, password=db_pass, database=DB_NAME
#  )
#def get_db_connection():
#    db_user, db_pass = get_db_credentials_from_vault()
#    # String de conexão usando o ODBC Driver 18 instalado no container
#    conn_str = (
#        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
#        f"SERVER={DB_SERVER};"
#        f"DATABASE={DB_NAME};"
#        f"UID={db_user};"
#        f"PWD={db_pass};"
#        f"TrustServerCertificate=yes;"
#    )
#    return pyodbc.connect(conn_str)

def get_db_connection():
    db_user, db_pass = get_db_credentials_from_vault()
    
    # 1. Tenta garantir que o banco 'appdb' existe conectando primeiro ao 'master'
    master_conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE=master;"
        f"UID={db_user};"
        f"PWD={db_pass};"
        f"TrustServerCertificate=yes;"
    )
    
    # Aguarda o SQL Server responder (evita timeout se o container acabou de subir)
    for i in range(10):
        try:
            temp_conn = pyodbc.connect(master_conn_str, timeout=3)
            temp_conn.autocommit = True
            cursor = temp_conn.cursor()
            # Cria o banco se não existir
            cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{DB_NAME}') CREATE DATABASE {DB_NAME};")
            temp_conn.close()
            break
        except Exception:
            time.sleep(3)

    # 2. Conecta no banco de dados final 'appdb' e garante que a tabela 'items' existe
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={db_user};"
        f"PWD={db_pass};"
        f"TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str)
    
    # Garante a criação da tabela items se ela não existir
    cursor = conn.cursor()
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='items' and xtype='U')
        CREATE TABLE items (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(100) NOT NULL,
            description NVARCHAR(255)
        )
    """)
    conn.commit()
    
    return conn

# --- DECORADOR DE VALIDAÇÃO DE JWT (O "Segurança" da API) ---
def token_required(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    token = None
    if "Authorization" in request.headers:
      auth_header = request.headers["Authorization"]
      try:
        token = auth_header.split(" ")[1]
      except IndexError:
        return (
            jsonify({"error": "Token mal formatado. Use Bearer <token>"}),
            401,
        )

    if not token:
      return jsonify({"error": "Token de autenticação ausente!"}), 401

    try:
      # 1. Pega o cabeçalho do token para descobrir qual 'kid' (Key ID) foi usado para assinar
      unverified_header = jwt.get_unverified_header(token)
      kid = unverified_header.get("kid")

      # 2. Baixa o conjunto de chaves públicas do Keycloak (JWKS)
      jwks_response = requests.get(KEYCLOAK_JWKS_URL)
      jwks = jwks_response.json()

      # 3. Encontra a chave pública correspondente ao 'kid' do token
      public_key = None
      for key in jwks.get("keys", []):
        if key.get("kid") == kid:
          # Converte a chave JWK para o formato PEM que o PyJWT entende
          public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
          break

      if not public_key:
        return (
            jsonify({"error": "Chave pública não encontrada para este token"}),
            401,
        )

      # 4. Valida a assinatura, expiração e o emissor usando a chave pública do Keycloak
      data = jwt.decode(
          token,
          public_key,
          algorithms=["RS256"],
          options={
              "verify_audience": False
          },  # Ajuste conforme as configurações de client do Keycloak se necessário
      )
      current_user = data.get("preferred_username") or data.get("sub")

    except jwt.ExpiredSignatureError:
      return jsonify({"error": "Token do Keycloak expirado!"}), 401
    except jwt.InvalidTokenError as e:
      return jsonify({"error": f"Token inválido: {str(e)}"}), 401
    except Exception as e:
      return jsonify({"error": f"Erro na validação do token: {str(e)}"}), 500

    return f(*args, **kwargs)

  return decorated


@app.route("/", methods=["GET"])
def home():
  return jsonify({"status": "API AppSec Lab rodando com sucesso!"})


# GET: Listar itens (Protegido por JWT)
@app.route("/items", methods=["GET"])
@token_required
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


# POST: Criar item (Protegido por JWT)
@app.route("/items", methods=["POST"])
@token_required
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
            "INSERT INTO items (name, description) VALUES (?, ?)",
            (name, description),
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Item criado com sucesso!"}), 201
    except Exception as e:
        print(f"Erro ao inserir item: {str(e)}") # Exibe no log do docker
        return jsonify({"error": str(e)}), 500

# DELETE: Deletar um item por ID
@app.route("/items/<int:item_id>", methods=["DELETE"])
@token_required
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
