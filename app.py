# Aplicação Flask Principal
from flask import Flask
from config import SECRET_KEY
from routes import register_blueprints

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Registar todos os blueprints
register_blueprints(app)

# Executa o servidor apenas se o ficheiro for executado diretamente
if __name__ == '__main__':
    # Inicia o servidor Flask em modo debug (mostra erros detalhados)
    app.run(debug=True)