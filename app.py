from flask import Flask, redirect, render_template, request, jsonify, session, flash
import pyodbc
import hashlib

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui_123'  # Necessário para sessões

# Configuração da base de dados
DB_CONFIG = {
    'server': 'tcp:mednat.ieeta.pt\\SQLSERVER,8101',
    'database': 'p1g7',
    'username': 'p1g7',
    'password': '-375018182@BD'
}

# Função para obter conexão com a BD (SQL Server Authentication)
def get_db_connection():
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']}"
    return pyodbc.connect(conn_str)

# Função geral para gerar IDs únicos para qualquer tabela
def generate_id(table_name, id_column):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"SELECT ISNULL(MAX({id_column}), 0) + 1 FROM {table_name}"
    cursor.execute(query) 
    new_id = cursor.fetchone()[0]
    conn.close()
    return new_id

@app.route('/')
def homepage():
    return render_template('homepage.html')

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
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Precisa fazer login para aceder a esta página!', 'redirect': '/login'}), 401
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM Diretor_de_Corrida WHERE id_utilizador=?',(session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    conn.close()
    return render_template('WelcomeDC.html')

@app.route('/welcomeDP')
def welcomeDP():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Precisa fazer login para aceder a esta página!', 'redirect': '/login'}), 401
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador=?',(session['id'],))
    if cursor.fetchone() is None:
        conn.close()
        return redirect('/logout')
    conn.close()
    return render_template('WelcomeDP.html')

@app.route('/welcomeTP')
def welcomeTP():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Precisa fazer login para aceder a esta página!', 'redirect': '/login'}), 401 
    conn=get_db_connection()
    cursor=conn.cursor()
    cursor.execute('SELECT * FROM Tecnico_de_Pista WHERE id_utilizador=?',(session['id'],))
    if cursor.fetchone() is None:
        conn.close()
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

                cursor.execute('SELECT * FROM Tecnico_de_Pista WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'tecnico'
                    conn.close()
                    return jsonify({'success': True, 'redirect': '/welcomeTP'})
                cursor.execute('SELECT * FROM Diretor_de_Equipa WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'Diretor_de_Equipa'
                    conn.close()
                    return jsonify({'success': True, 'redirect': '/welcomeDP'})
                cursor.execute('SELECT * FROM Diretor_de_Corrida WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'Diretor_de_Corrida'
                    conn.close()
                    return jsonify({'success': True, 'redirect': '/welcomeDC'})
                conn.close()
                return jsonify({'success': False, 'message': 'Utilizador não tem nenhum perfil atribuído!'}), 401
            else:
                conn.close()
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
            username = data['username']
            email = data['email']
            password = data['password']
            tipo = data['role']
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Inserir utilizador (ID é gerado automaticamente pelo IDENTITY)
            cursor.execute(
                "INSERT INTO Utilizador (username, email, password, nome) OUTPUT INSERTED.ID_utilizador VALUES (?, ?, ?, ?)",
                (username, email, password, nome)
            )
            id_utilizador = cursor.fetchone()[0]
            
            if tipo == 'tecnico':
                cursor.execute("INSERT INTO Tecnico_de_Pista (id_utilizador) VALUES (?)", (id_utilizador,))
            elif tipo == 'Diretor_de_Equipa':
                cursor.execute("INSERT INTO Diretor_de_Equipa (id_utilizador) VALUES (?)", (id_utilizador,))
            elif tipo == 'Diretor_de_Corrida':
                cursor.execute("INSERT INTO Diretor_de_Corrida (id_utilizador) VALUES (?)", (id_utilizador,))
            
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