with open('migrations/env.py') as f:
    content = f.read()
    for line in content.split('\n'):
        if 'sqlalchemy' in line.lower() or 'url' in line.lower() or 'dialect' in line.lower() or 'password' in line.lower():
            print(line)