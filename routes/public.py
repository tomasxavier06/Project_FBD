# Rotas públicas (acessíveis sem autenticação)
from flask import Blueprint, render_template, request, jsonify
from utils.database import get_db_connection

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def homepage():
    return render_template('homepage.html')


@public_bp.route('/pilots')
def pilots():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        pesquisa = request.args.get('nome_procurado')
        coluna = request.args.get('coluna', 'nome')
        ordem = request.args.get('ordem', 'asc')

        colunas_validas = ['numero_licenca', 'nome', 'data_nascimento', 'nacionalidade', 'nome_equipa', 'numero_eventos']

        if coluna not in colunas_validas:
            coluna = 'nome'

        if ordem.lower() not in ['asc', 'desc']:
            ordem = 'asc'

        query = """ SELECT P.numero_licenca, P.nome, P.data_nascimento, P.nacionalidade, E.nome AS nome_equipa, P.numero_eventos
                    FROM Piloto P
                    LEFT JOIN Equipa E ON P.id_equipa = E.id_equipa """
        parametros = []

        if pesquisa:
            query += "WHERE (P.nome LIKE ? OR E.nome LIKE ? OR P.nacionalidade LIKE ?)"
            parametros.append(f"%{pesquisa}%")
            parametros.append(f"%{pesquisa}%")
            parametros.append(f"%{pesquisa}%")

                    
        query += f" ORDER BY {coluna} {ordem}"
        
        cursor.execute(query, tuple(parametros))

        pilotos = cursor.fetchall()
        conn.close()
        return render_template('pilots.html', pilotos=pilotos, ordem_atual=ordem, coluna_ativa=coluna, pesquisa_feita=pesquisa)
    except Exception as e:
        print(f"erro real: {e}")
        return "<h3>Não foi possível carregar os pilotos. Tente novamente</h3>"


@public_bp.route('/teams')
def teams():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        pesquisa = request.args.get('nome_procurado')
        coluna = request.args.get('coluna', 'nome')
        ordem = request.args.get('ordem', 'asc')

        colunas_validas = ['id_equipa', 'nome', 'pais', 'ID_utilizador_diretor_de_equipa']

        if coluna not in colunas_validas:
            coluna = 'nome'

        if ordem.lower() not in ['asc', 'desc']:
            ordem = 'asc'

        query = " SELECT * FROM Equipa "
        parametros = []

        if pesquisa:
            query += "WHERE (nome LIKE ? OR pais LIKE ?)"
            parametros.append(f"%{pesquisa}%")
            parametros.append(f"%{pesquisa}%")

        query += f" ORDER BY {coluna} {ordem}"
        
        cursor.execute(query, tuple(parametros))

        equipas_lista = cursor.fetchall()
        conn.close()
        return render_template('teams.html', equipas=equipas_lista, ordem_atual=ordem, coluna_ativa=coluna, pesquisa_feita=pesquisa)
    except Exception as e:
        print(f"erro real: {e}")
        return "<h3>Não foi possível carregar as equipas. Tente novamente</h3>"


@public_bp.route('/team/<int:id>')
def team_details(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT nome, pais FROM Equipa WHERE id_equipa = ?", (id,))
        equipa = cursor.fetchone()

        if not equipa:
            conn.close()
            return "<h3>Equipa não encontrada.</h3>", 404

        
        cursor.execute("""
            SELECT numero_licenca, nome, data_nascimento, nacionalidade 
            FROM Piloto WHERE id_equipa = ?
        """, (id,))
        pilotos = cursor.fetchall()


        cursor.execute("""
            SELECT VIN, marca, modelo, categoria 
            FROM Carro WHERE id_equipa = ?
        """, (id,))
        carros = cursor.fetchall()

        conn.close()
        return render_template('team_details.html', equipa=equipa, pilotos=pilotos, carros=carros)
    except Exception as e:
        print(f"Erro ao carregar detalhes da equipa: {e}")
        return "<h3>Erro ao carregar detalhes.</h3>"


@public_bp.route('/events')
def events():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # garante que os status estão atualizados antes de listar
        cursor.execute("EXEC sp_ManutencaoStatusEventos")
        conn.commit()
        
        # lista os eventos com os totais 
        cursor.execute("EXEC sp_ListarEventosComTotais")
        eventos = cursor.fetchall()
        
        conn.close()
        return render_template('events.html', eventos=eventos)
    except Exception as e:
        return f"Erro: {e}"


@public_bp.route('/api/lap_details/<int:id_volta>')
def lap_details(id_volta):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # query que junta a Volta com a Sessão para obter os dados técnicos
        query = """
            SELECT 
                S.temperatura_asfalto, S.temperatura_ar, S.humidade, S.precipitação,
                V.pressao_pneus, V.numero_volta, S.tipo as tipo_sessao,
                dbo.fn_FormatarTempoMS(V.tempo) as tempo
            FROM Volta V
            INNER JOIN Sessao S ON V.id_sessao = S.id_sessao
            WHERE V.id_volta = ?
        """
        cursor.execute(query, (id_volta,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return jsonify({
                'temp_asfalto': row[0], 'temp_ar': row[1],
                'humidade': row[2], 'precipitacao': row[3],
                'pressao': row[4], 'volta_n': row[5],
                'sessao': row[6], 'tempo': row[7]
            })
        return jsonify({'error': 'Não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@public_bp.route('/records')
def records():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Obter listas para os dropdowns (Filtros Tradicionais)
        # Nota: ORDER BY deve coincidir com o SELECT DISTINCT para evitar o erro 42000
        cursor.execute("SELECT DISTINCT nome FROM Piloto ORDER BY nome")
        lista_pilotos = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT DISTINCT (marca + ' ' + modelo) 
            FROM Carro 
            ORDER BY (marca + ' ' + modelo)
        """)
        lista_carros = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT nome FROM Evento ORDER BY nome")
        lista_eventos = [row[0] for row in cursor.fetchall()]

        # 2. Capturar os filtros selecionados via GET
        f_piloto = request.args.get('piloto', '')
        f_carro = request.args.get('carro', '')
        f_evento = request.args.get('evento', '')

        # 3. Query Principal de Recordes usando a UDF fn_FormatarTempoMS
        query = """
            SELECT 
                dbo.fn_FormatarTempoMS(V.tempo) as tempo_formatado,
                P.nome as piloto,
                C.marca + ' ' + C.modelo as carro,
                Ev.nome as evento,
                V.tempo,
                S.data,
                V.id_volta
            FROM Volta V
            INNER JOIN Piloto P ON V.numero_licenca = P.numero_licenca
            INNER JOIN Carro C ON V.carro_VIN = C.VIN
            INNER JOIN Sessao S ON V.id_sessao = S.id_sessao
            INNER JOIN Evento Ev ON S.id_evento = Ev.id_evento
            WHERE 1=1
        """
        params = []

        # Aplicação dos filtros via Dropdowns (comparações exatas)
        if f_piloto:
            query += " AND P.nome = ?"
            params.append(f_piloto)
        if f_carro:
            query += " AND (C.marca + ' ' + C.modelo) = ?"
            params.append(f_carro)
        if f_evento:
            query += " AND Ev.nome = ?"
            params.append(f_evento)

        # Ordenar pelo tempo real (milissegundos) do mais rápido para o mais lento
        query += " ORDER BY V.tempo ASC"

        cursor.execute(query, params)
        recordes = cursor.fetchall()
        conn.close()

        # 4. Renderizar o template com todas as listas e filtros
        return render_template('records.html', 
                               recordes=recordes,
                               lista_pilotos=lista_pilotos,
                               lista_carros=lista_carros,
                               lista_eventos=lista_eventos,
                               f_piloto=f_piloto,
                               f_carro=f_carro,
                               f_evento=f_evento)
    except Exception as e:
        print(f"Erro detalhado nos recordes: {e}")
        return f"<h3>Erro ao carregar a página de recordes: {e}</h3>"
