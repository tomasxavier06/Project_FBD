from flask import Flask, redirect, render_template, request, jsonify, session
import pyodbc
import hashlib

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_123'  # Necessário para sessões

# Configuração da base de dados
DB_CONFIG = {
    'server': 'DESKTOP-4ATM5KE\\SQLEXPRESS',
    'database': 'p1g7'
}

# Função para obter conexão com a BD (Windows Authentication)
def get_db_connection():
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};Trusted_Connection=yes"
    return pyodbc.connect(conn_str)

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/hpafterlogin')
def hpafterlogin():
    return render_template('hpafterlogin.html')

@app.route('/pilots')
def pilots():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Piloto")
    pilotos = cursor.fetchall()
    conn.close()
    return render_template('pilots.html', pilotos=pilotos)

@app.route('/teams')
def teams():
    # Retorna o template teams.html
    return render_template('teams.html')

# Define a rota para a página de eventos
@app.route('/events')
def events():
    # Retorna o template events.html
    return render_template('events.html')

# Define a rota para a página de recordes
@app.route('/records')
def records():
    # Retorna o template records.html
    return render_template('records.html')

@app.route('/welcomeDC')
def welcomeDC():
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM Diretor_Corrida WHERE id_utilizador=?',(session['id'],))
    if cursor.fetchone() is None:
        return redirect('/logout')
    conn.close()
    return render_template('WelcomeDC.html')

@app.route('/welcomeDP')
def welcomeDP():
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM Diretor_Pista WHERE id_utilizador=?',(session['id'],))
    if cursor.fetchone() is None:
        return redirect('/logout')
    conn.close()
    return render_template('WelcomeDP.html')

@app.route('/welcomeTP')
def welcomeTP():
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM Tecnico_Pista WHERE id_utilizador=?',(session['id'],))
    if cursor.fetchone() is None:
        return redirect('/logout')
    conn.close()
    return render_template('WelcomeTP.html')

# Define a rota para a página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data['username']
            password = data['password']
            conn = get_db_connection()  
            cursor = conn.cursor()
            cursor.execute('SELECT id_utilizador, username, email FROM Utilizador WHERE username = ? AND password = ?', (username, password))
            utilizador = cursor.fetchone()
            if utilizador:
                id_utilizador = utilizador[0]
                session['loggedin'] = True
                session['id'] = id_utilizador
                session['username'] = utilizador[1]

                cursor.execute('SELECT * FROM Tecnico_Pista WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'tecnico'
                    return jsonify({'success': True, 'redirect': '/welcomeTP'})
                cursor.execute('SELECT * FROM Diretor_Equipa WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'diretor_equipa'
                    return jsonify({'success': True, 'redirect': '/welcomeDC'})
                cursor.execute('SELECT * FROM Diretor_Corrida WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'diretor_corrida'
                    return jsonify({'success': True, 'redirect': '/welcomeDP'})
                conn.close()
                return jsonify({'success': True, 'message': 'Login efetuado com sucesso!'})
            else:
                return jsonify({'success': False, 'message': 'Username ou password incorretos!'}), 401
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.get_json()
            nome = data['name']
            email = data['email']
            password = data['password']
            tipo = data['role']
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Inserir utilizador
            cursor.execute(
                "INSERT INTO Utilizador (username, email, password) OUTPUT INSERTED.id_utilizador VALUES (?, ?, ?)",
                (nome, email, password)
            )
            id_utilizador = cursor.fetchone()[0]
            
            if tipo == 'tecnico':
                cursor.execute("INSERT INTO Tecnico_Pista (id_utilizador) VALUES (?)", (id_utilizador,))
            elif tipo == 'diretor_equipa':
                cursor.execute("INSERT INTO Diretor_Equipa (id_utilizador) VALUES (?)", (id_utilizador,))
            elif tipo == 'diretor_corrida':
                cursor.execute("INSERT INTO Diretor_Corrida (id_utilizador) VALUES (?)", (id_utilizador,))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Utilizador registado com sucesso!'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    
    # GET request - retorna o template
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Executa o servidor apenas se o ficheiro for executado diretamente
if __name__ == '__main__':
    # Inicia o servidor Flask em modo debug (mostra erros detalhados)
    app.run(debug=True)