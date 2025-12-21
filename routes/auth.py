# Rotas de autenticação
from flask import Blueprint, render_template, request, jsonify, session, redirect
import hashlib
from utils.database import get_db_connection

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data['username']
            password = data['password']
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id_utilizador, username, email FROM Utilizador WHERE username = ? AND password = ?', (username, password_hash))
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
                    return jsonify({'success': True, 'redirect': '/welcomeDE'})
                cursor.execute('SELECT * FROM Diretor_de_Corrida WHERE id_utilizador = ?', (id_utilizador,))
                if cursor.fetchone():
                    session['role'] = 'Diretor_de_Corrida'
                    conn.close()
                    return jsonify({'success': True, 'redirect': '/welcomeDC'})
                conn.close()
                return jsonify({'success': False, 'message': 'Utilizador sem tipo definido. Contacte o administrador.'}), 400
            else:
                conn.close()
                return jsonify({'success': False, 'message': 'Username ou password incorretos!'}), 401
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.get_json()
            nome = data['name']
            username = data['username']
            email = data['email']
            password = data['password']
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            tipo = data['role']
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Inserir utilizador com password hasheada
            cursor.execute(
                "INSERT INTO Utilizador (username, email, password, nome) OUTPUT INSERTED.ID_utilizador VALUES (?, ?, ?, ?)",
                (username, email, password_hash, nome)
            )
            id_utilizador = cursor.fetchone()[0]
            
            print(f"DEBUG: tipo recebido = '{tipo}'")
            print(f"DEBUG: id_utilizador = {id_utilizador}")
            
            if tipo == 'tecnico_de_pista':
                print("DEBUG: Inserindo em Tecnico_de_Pista")
                cursor.execute("INSERT INTO Tecnico_de_Pista (id_utilizador) VALUES (?)", (id_utilizador,))
            elif tipo == 'diretor_de_equipa':
                print("DEBUG: Inserindo em Diretor_de_Equipa")
                cursor.execute("INSERT INTO Diretor_de_Equipa (id_utilizador) VALUES (?)", (id_utilizador,))
            elif tipo == 'diretor_de_corrida':
                print("DEBUG: Inserindo em Diretor_de_Corrida")
                cursor.execute("INSERT INTO Diretor_de_Corrida (id_utilizador) VALUES (?)", (id_utilizador,))
            else:
                print(f"DEBUG: TIPO NÃO RECONHECIDO: '{tipo}'")
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Utilizador registado com sucesso!'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    
    # GET request - retorna o template
    return render_template('register.html')


@auth_bp.route('/settings')
def settings():
    if 'loggedin' not in session:
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT username, email, nome FROM Utilizador WHERE ID_utilizador=?", (session['id'],))
    user = cursor.fetchone()
    conn.close()
    
    if user is None:
        return redirect('/logout')
    
    return render_template('settings.html', username=user[0], email=user[1], nome=user[2])


@auth_bp.route('/api/settings', methods=['PUT'])
def update_settings():
    if 'loggedin' not in session:
        return jsonify({'success': False, 'message': 'Não autenticado'}), 401
    
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update name
        if data.get('nome'):
            cursor.execute("UPDATE Utilizador SET nome=? WHERE ID_utilizador=?", (data['nome'], session['id']))
        
        # Update password if provided
        if data.get('password_atual') and data.get('password_nova'):
            # Verify current password
            cursor.execute("SELECT password FROM Utilizador WHERE ID_utilizador=?", (session['id'],))
            user = cursor.fetchone()
            
            password_hash = hashlib.sha256(data['password_atual'].encode()).hexdigest()
            if user[0] != password_hash:
                conn.close()
                return jsonify({'success': False, 'message': 'Password atual incorreta!'}), 400
            
            # Update password
            new_password_hash = hashlib.sha256(data['password_nova'].encode()).hexdigest()
            cursor.execute("UPDATE Utilizador SET password=? WHERE ID_utilizador=?", (new_password_hash, session['id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Definições atualizadas com sucesso!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')
