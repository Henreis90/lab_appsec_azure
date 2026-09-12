#docker exec -it keycloak_lab /opt/keycloak/bin/kcadm.sh config credentials   --server http://localhost:8080   --realm master   --user admin   --password KeycloakAdminSecure123

#docker exec -it keycloak_lab /opt/keycloak/bin/kcadm.sh create users   -r master   -s username=joao   -s enabled=true && docker exec -it keycloak_lab /opt/keycloak/bin/kcadm.sh set-password   -r master   --username joao   --new-password Senha123!

TOKEN=$(curl -s -X POST "http://localhost:9080/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli" \
  -d "username=joao" \
  -d "password=Senha123!" \
  -d "grant_type=password" | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')

curl -X POST http://localhost:8080/items \
  -H "Authorization: Bearer \$TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Servidor Lab AppSec", "descricao": "Laboratório de isolamento e Keycloak"}'

curl -X GET http://localhost:8080/items   -H "Authorization: Bearer $TOKEN"
 
