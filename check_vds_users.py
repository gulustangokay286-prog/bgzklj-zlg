import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("213.142.159.36", username="root", password="wiZJevCTpujLNy2X", timeout=10)

stdin, stdout, stderr = ssh.exec_command('docker exec bogazici_db psql -U postgres -d bogazici_db -c "SELECT id, email FROM users;"')
print("USERS IN VDS DB:")
print(stdout.read().decode())
print(stderr.read().decode())
