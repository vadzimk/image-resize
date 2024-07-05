#!/bin/bash

set -Eeuo pipefail

mongosh -u "${MONGO_INITDB_ROOT_USERNAME}" -p "${MONGO_INITDB_ROOT_PASSWORD}" --authenticationDatabase admin "${MONGO_DATABASE_NAME}" <<EOF
  db.createUser({
        user: '$MONGO_APP_USERNAME',
        pwd: '$MONGO_APP_PASSWORD',
        roles: [ { role: 'readWrite', db: '$MONGO_DATABASE_NAME' } ]
  })
EOF