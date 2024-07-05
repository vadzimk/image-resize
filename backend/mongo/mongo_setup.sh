mongodb1=mongo1
mongodb2=mongo2
mongodb3=mongo3

mongodb1_ready() {
    # Attempt to connect to MongoDB and check if it's responsive
    if echo "db.adminCommand('ping')" | mongosh --quiet --host ${mongodb1}:30001 -u ${MONGO_INITDB_ROOT_USERNAME} -p ${MONGO_INITDB_ROOT_PASSWORD} >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

until mongodb1_ready
do
  echo "Waiting for startup ${mongodb1}, at time UTC: $(date +"%T")";
  sleep 1;
done

echo "Setup Begin at time UTC: $(date +"%T")"
mongosh --host ${mongodb1}:30001 -u ${MONGO_INITDB_ROOT_USERNAME} -p ${MONGO_INITDB_ROOT_PASSWORD} <<EOF
disableTelemetry();
var cfg = {
  "_id": "${MONGO_REPLICA_SET_NAME}",
  "protocolVersion": 1,
  "version": 1,
  "members": [
    {
      "_id": 0,
      "host": "${mongodb1}:30001",
      "priority": 2
    },
    {
      "_id": 1,
      "host": "${mongodb2}:30002",
      "priority": 0
    },
    {
      "_id": 2,
      "host": "${mongodb3}:30003",
      "priority": 0
    },
  ]
};
rs.initiate(cfg, {force: true});
rs.secondaryOk();
db.getMongo().setReadPref('primary');
rs.status();
EOF
echo "Setup Done at time UTC: $(date +"%T")"