import paramiko
import sys
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('213.142.159.36', username='root', password='wiZJevCTpujLNy2X')
    cmd = 'find /root -name "*main.py" 2>/dev/null'
    stdin, stdout, stderr = client.exec_command(cmd)
    paths = [p for p in stdout.read().decode('utf-8').strip().split('\n') if p]
    print('Found paths:', paths)
    for path in paths:
        if 'bogazici' in path.lower() or 'api' in path.lower() or 'vds' in path.lower():
            print(f'Fetching {path}...')
            stdin, stdout, stderr = client.exec_command(f'cat {path}')
            with open('downloaded_backend.py', 'w', encoding='utf-8') as f:
                f.write(stdout.read().decode('utf-8'))
            print('Downloaded to downloaded_backend.py')
            break
except Exception as e:
    print('Error:', e)
finally:
    client.close()
