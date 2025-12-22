CREATE TABLE Utilizador (
    ID_utilizador INT IDENTITY(1,1) PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL
);

CREATE TABLE Diretor_de_Corrida (
    ID_utilizador INT PRIMARY KEY,
    FOREIGN KEY (ID_utilizador) REFERENCES Utilizador(ID_utilizador) ON DELETE CASCADE
);

CREATE TABLE Diretor_de_Equipa (
    ID_utilizador INT PRIMARY KEY,
    FOREIGN KEY (ID_utilizador) REFERENCES Utilizador(ID_utilizador) ON DELETE CASCADE
);

CREATE TABLE Tecnico_de_Pista (
    ID_utilizador INT PRIMARY KEY,
    FOREIGN KEY (ID_utilizador) REFERENCES Utilizador(ID_utilizador) ON DELETE CASCADE
);

CREATE TABLE Equipa (
    id_equipa INT IDENTITY(1,1) PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    pais VARCHAR(50) NOT NULL,
    ID_utilizador_diretor_de_equipa INT UNIQUE,
    FOREIGN KEY (ID_utilizador_diretor_de_equipa) REFERENCES Diretor_de_Equipa(ID_utilizador)
);

CREATE TABLE Piloto (
    numero_licenca INT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    data_nascimento DATE NOT NULL,
    nacionalidade VARCHAR(50) NOT NULL,
    id_equipa INT,
    numero_eventos INT DEFAULT 0,
    FOREIGN KEY (id_equipa) REFERENCES Equipa(id_equipa)
);

CREATE TABLE Carro (
    VIN VARCHAR(50) PRIMARY KEY,
    modelo VARCHAR(100) NOT NULL,
    marca VARCHAR(100) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    tipo_motor VARCHAR(50),
    potencia INT,
    peso INT,
    id_equipa INT,
    FOREIGN KEY (id_equipa) REFERENCES Equipa(id_equipa)
);

CREATE TABLE Evento (
    id_evento INT IDENTITY(1,1) PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Por Iniciar',
    ID_utilizador_gestor_de_corrida INT,
    FOREIGN KEY (ID_utilizador_gestor_de_corrida) REFERENCES Diretor_de_Corrida(ID_utilizador),
    CONSTRAINT CK_Evento_Datas CHECK (data_fim >= data_inicio)
);

CREATE TABLE Sessao (
    id_sessao INT IDENTITY(1,1) PRIMARY KEY,
    data DATE NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    temperatura_asfalto INT,
    temperatura_ar INT,
    humidade INT,
    precipitacao INT,
    id_evento INT NOT NULL,
    hora_inicio TIME,
    hora_fim TIME,
    status VARCHAR(20) DEFAULT 'Por Iniciar',
    FOREIGN KEY (id_evento) REFERENCES Evento(id_evento) ON DELETE CASCADE --TEM REDUNDANCIA COM FRONTEND ALTERAR
);

CREATE TABLE Volta (
    id_volta INT IDENTITY(1,1) PRIMARY KEY,
    id_sessao INT NOT NULL,
    numero_licenca INT NOT NULL,
    carro_VIN VARCHAR(50) NOT NULL,
    tempo INT NOT NULL,
    numero_volta INT NOT NULL,
    data_hora DATETIME DEFAULT GETDATE(),
    pressao_pneus INT,
    ID_utilizador_tecnico_de_pista INT,
    FOREIGN KEY (id_sessao) REFERENCES Sessao(id_sessao),
    FOREIGN KEY (numero_licenca) REFERENCES Piloto(numero_licenca),
    FOREIGN KEY (carro_VIN) REFERENCES Carro(VIN),
    FOREIGN KEY (ID_utilizador_tecnico_de_pista) REFERENCES Tecnico_de_Pista(ID_utilizador),
    CONSTRAINT UQ_Volta_Sessao_Carro_Numero UNIQUE (id_sessao, carro_VIN, numero_volta)
);

CREATE TABLE Participa_Sessao (
    id_sessao INT NOT NULL,
    numero_licenca INT NOT NULL,   
    VIN_carro VARCHAR(50) NOT NULL,        
    combustivel_inicial INT,
    pressao_pneus INT,
    configuracao_aerodinamica INT,
    PRIMARY KEY (id_sessao, numero_licenca, VIN_carro),
    FOREIGN KEY (id_sessao) REFERENCES Sessao(id_sessao) ON DELETE CASCADE,
    FOREIGN KEY (numero_licenca) REFERENCES Piloto(numero_licenca),
    FOREIGN KEY (VIN_carro) REFERENCES Carro(VIN),
    CONSTRAINT UQ_Piloto_Sessao UNIQUE (id_sessao, numero_licenca),
    CONSTRAINT UQ_Carro_Sessao UNIQUE (id_sessao, VIN_carro)
);

CREATE TABLE Participa_Evento (
    id_equipa INT NOT NULL,
    id_evento INT NOT NULL,
    PRIMARY KEY (id_equipa, id_evento),
    FOREIGN KEY (id_equipa) REFERENCES Equipa(id_equipa),
    FOREIGN KEY (id_evento) REFERENCES Evento(id_evento) ON DELETE CASCADE
);

-- UDF: Converter "mm:ss:ms" para milissegundos
CREATE FUNCTION dbo.TempoParaMs (@tempo VARCHAR(12))
RETURNS INT
AS
BEGIN
    DECLARE @minutos INT, @segundos INT, @ms INT;
    SET @minutos = CAST(SUBSTRING(@tempo, 1, 2) AS INT);
    SET @segundos = CAST(SUBSTRING(@tempo, 4, 2) AS INT);
    SET @ms = CAST(SUBSTRING(@tempo, 7, 2) AS INT) * 10;
    RETURN (@minutos * 60000) + (@segundos * 1000) + @ms;
END;
GO

-- Stored Procedure: registar Volta
CREATE PROCEDURE dbo.sp_RegistarVolta
    @id_sessao INT,
    @numero_licenca INT,
    @carro_VIN VARCHAR(50),
    @tempo_str VARCHAR(12),
    @numero_volta INT,
    @pressao_pneus INT,
    @id_tecnico INT
AS
BEGIN
    INSERT INTO Volta (id_sessao, numero_licenca, carro_VIN, tempo, numero_volta, data_hora, pressao_pneus, ID_utilizador_tecnico_de_pista)
    VALUES (@id_sessao, @numero_licenca, @carro_VIN, dbo.TempoParaMs(@tempo_str), @numero_volta, GETDATE(), @pressao_pneus, @id_tecnico);
END;
GO

CREATE TRIGGER trg_AtualizarNumeroEventos
ON Volta
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    
    UPDATE P
    SET P.numero_eventos = ISNULL(P.numero_eventos, 0) + 1
    FROM Piloto P
    INNER JOIN inserted i ON P.numero_licenca = i.numero_licenca
    INNER JOIN Sessao S ON i.id_sessao = S.id_sessao
    WHERE NOT EXISTS (
        SELECT 1 
        FROM Volta v2
        INNER JOIN Sessao s2 ON v2.id_sessao = s2.id_sessao
        WHERE v2.numero_licenca = i.numero_licenca
          AND s2.id_evento = S.id_evento
          AND v2.id_volta != i.id_volta
    );
END;
GO

CREATE TRIGGER trg_ValidarCondicoesVolta
ON Volta
INSTEAD OF INSERT
AS
BEGIN
    SET NOCOUNT ON;
    
    -- verifica se a sessão tem condições climáticas registadas
    IF EXISTS (
        SELECT 1 FROM inserted i
        INNER JOIN Sessao S ON i.id_sessao = S.id_sessao
        WHERE S.temperatura_asfalto IS NULL 
           OR S.temperatura_ar IS NULL 
           OR S.humidade IS NULL
    )
    BEGIN
        RAISERROR('Não é possível registar voltas. As condições climáticas da sessão ainda não foram registadas!', 16, 1);
        RETURN;
    END
    
    -- se passou a validação, inserir a volta
    INSERT INTO Volta (id_sessao, numero_licenca, carro_VIN, tempo, numero_volta, data_hora, pressao_pneus, ID_utilizador_tecnico_de_pista)
    SELECT id_sessao, numero_licenca, carro_VIN, tempo, numero_volta, GETDATE(), pressao_pneus, ID_utilizador_tecnico_de_pista
    FROM inserted;
END;
GO

-- SP: adicionar Piloto (com validação)
CREATE PROCEDURE sp_AdicionarPiloto
    @numero_licenca INT,
    @nome VARCHAR(100),
    @data_nascimento DATE,
    @nacionalidade VARCHAR(50),
    @id_equipa INT
AS
BEGIN
    -- Verificar se já existe
    IF EXISTS (SELECT 1 FROM Piloto WHERE numero_licenca = @numero_licenca)
    BEGIN
        RAISERROR('Já existe um piloto com este número de licença!', 16, 1);
        RETURN;
    END
    
    INSERT INTO Piloto (numero_licenca, nome, data_nascimento, nacionalidade, id_equipa, numero_eventos)
    VALUES (@numero_licenca, @nome, @data_nascimento, @nacionalidade, @id_equipa, 0);
END;
GO

-- SP: Vincular Piloto Existente a Equipa
CREATE PROCEDURE sp_VincularPiloto
    @numero_licenca INT,
    @id_equipa INT
AS
BEGIN
    UPDATE Piloto SET id_equipa = @id_equipa 
    WHERE numero_licenca = @numero_licenca AND id_equipa IS NULL;
    
    IF @@ROWCOUNT = 0
        RAISERROR('Piloto não encontrado ou já vinculado a outra equipa!', 16, 1);
END;
GO

-- SP: Adicionar Carro (com validação)
CREATE PROCEDURE sp_AdicionarCarro
    @VIN VARCHAR(50),
    @modelo VARCHAR(100),
    @marca VARCHAR(100),
    @categoria VARCHAR(50),
    @tipo_motor VARCHAR(50),
    @potencia INT,
    @peso INT,
    @id_equipa INT
AS
BEGIN
    -- Verificar se já existe
    IF EXISTS (SELECT 1 FROM Carro WHERE VIN = @VIN)
    BEGIN
        RAISERROR('Já existe um carro com este VIN!', 16, 1);
        RETURN;
    END
    
    INSERT INTO Carro (VIN, modelo, marca, categoria, tipo_motor, potencia, peso, id_equipa)
    VALUES (@VIN, @modelo, @marca, @categoria, @tipo_motor, @potencia, @peso, @id_equipa);
END;
GO

-- SP: Vincular Carro Existente a Equipa
CREATE PROCEDURE sp_VincularCarro
    @VIN VARCHAR(50),
    @id_equipa INT
AS
BEGIN
    UPDATE Carro SET id_equipa = @id_equipa 
    WHERE VIN = @VIN AND id_equipa IS NULL;
    
    IF @@ROWCOUNT = 0
        RAISERROR('Carro não encontrado ou já vinculado a outra equipa!', 16, 1);
END;
GO

-- SP: Cancelar Evento Completo (com transação)
CREATE PROCEDURE sp_CancelarEventoCompleto
    @id_evento INT
AS
BEGIN
    BEGIN TRANSACTION;
    BEGIN TRY
        -- Apagar participações nas sessões
        DELETE PS FROM Participa_Sessao PS
        INNER JOIN Sessao S ON PS.id_sessao = S.id_sessao
        WHERE S.id_evento = @id_evento;
        
        -- Apagar voltas
        DELETE V FROM Volta V
        INNER JOIN Sessao S ON V.id_sessao = S.id_sessao
        WHERE S.id_evento = @id_evento;
        
        -- Apagar participações de equipas
        DELETE FROM Participa_Evento WHERE id_evento = @id_evento;
        
        -- Apagar sessões
        DELETE FROM Sessao WHERE id_evento = @id_evento;
        
        -- Apagar evento
        DELETE FROM Evento WHERE id_evento = @id_evento;
        
        COMMIT;
    END TRY
    BEGIN CATCH
        ROLLBACK;
        THROW;
    END CATCH
END;
GO

CREATE PROCEDURE sp_ListarEventosComTotais
AS
BEGIN
    SELECT 
        E.id_evento, 
        E.nome, 
        E.tipo, 
        E.data_inicio, 
        E.data_fim, 
        E.status,
        COUNT(DISTINCT PE.id_equipa) AS total_equipas,
        COUNT(DISTINCT PS.numero_licenca) AS total_pilotos
    FROM Evento E
    LEFT JOIN Participa_Evento PE ON E.id_evento = PE.id_evento
    LEFT JOIN Sessao S ON E.id_evento = S.id_evento
    LEFT JOIN Participa_Sessao PS ON S.id_sessao = PS.id_sessao
    GROUP BY E.id_evento, E.nome, E.tipo, E.data_inicio, E.data_fim, E.status
    ORDER BY E.data_inicio DESC;
END;
GO
CREATE PROCEDURE sp_ManutencaoStatusEventos
AS
BEGIN
    -- 1. Passar para 'Concluído' eventos que já passaram da data
    UPDATE Evento 
    SET status = 'Concluído' 
    WHERE data_fim < CAST(GETDATE() AS DATE) 
    AND status != 'Concluído';

    -- 2. Passar para 'A Decorrer' eventos que começam hoje
    UPDATE Evento 
    SET status = 'A Decorrer' 
    WHERE data_inicio <= CAST(GETDATE() AS DATE) 
    AND data_fim >= CAST(GETDATE() AS DATE)
    AND status = 'Por Iniciar';
END;
GO
CREATE FUNCTION dbo.fn_FormatarTempoMS (@ms INT)
RETURNS VARCHAR(20)
AS
BEGIN
    DECLARE @minutos INT, @segundos INT, @milissegundos INT;
    DECLARE @resultado VARCHAR(20);

    SET @minutos = @ms / 60000;
    SET @segundos = (@ms % 60000) / 1000;
    SET @milissegundos = @ms % 1000;

    SET @resultado = RIGHT('0' + CAST(@minutos AS VARCHAR), 2) + ':' + 
                     RIGHT('0' + CAST(@segundos AS VARCHAR), 2) + '.' + 
                     RIGHT('00' + CAST(@milissegundos AS VARCHAR), 3);
    RETURN @resultado;
END;
GO
CREATE TRIGGER trg_AtualizarStatusEvento
ON Sessao
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    -- atualiza o evento para 'Concluído' se todas as suas sessões já tiverem terminado
    -- OU se a data_fim do evento já tiver passado em relação à data atual
    UPDATE Evento
    SET status = 'Concluído'
    FROM Evento E
    WHERE E.id_evento IN (SELECT DISTINCT id_evento FROM inserted)
    AND (
        NOT EXISTS (
            SELECT 1 FROM Sessao S 
            WHERE S.id_evento = E.id_evento 
            AND S.status != 'Concluída'
        )
        OR E.data_fim < CAST(GETDATE() AS DATE)
    );
END;
GO
CREATE FUNCTION dbo.fn_IdadePiloto(@numero_licenca INT)
RETURNS INT AS BEGIN
    RETURN (SELECT DATEDIFF(YEAR, data_nascimento, GETDATE()) FROM Piloto WHERE numero_licenca = @numero_licenca);
END;
GO 

CREATE FUNCTION dbo.fn_GapParaMelhor(@id_volta INT)
RETURNS INT AS BEGIN
    DECLARE @tempo INT, @id_sessao INT;
    SELECT @tempo = tempo, @id_sessao = id_sessao FROM Volta WHERE id_volta = @id_volta;
    RETURN @tempo - (SELECT MIN(tempo) FROM Volta WHERE id_sessao = @id_sessao);
END;
GO 

CREATE NONCLUSTERED INDEX IX_Utilizador_Login 
ON Utilizador(username, password) 
INCLUDE (id_utilizador, email);
GO

CREATE NONCLUSTERED INDEX IX_Volta_Tempo 
ON Volta(tempo ASC) 
INCLUDE (id_sessao, numero_licenca, carro_VIN);
GO

CREATE NONCLUSTERED INDEX IX_Piloto_Nome 
ON Piloto(nome) 
INCLUDE (numero_licenca, data_nascimento, nacionalidade, id_equipa, numero_eventos);
GO

-- View: Ranking de pilotos para listagem
CREATE VIEW vw_RankingPilotos AS
SELECT 
    P.numero_licenca,
    P.nome,
    P.data_nascimento,
    P.nacionalidade,
    E.nome AS nome_equipa,
    P.numero_eventos,
    P.id_equipa,
    dbo.fn_IdadePiloto(P.numero_licenca) as idade
FROM Piloto P
LEFT JOIN Equipa E ON P.id_equipa = E.id_equipa;
GO

-- View: Recordes para página de tempos
CREATE VIEW vw_Recordes AS
SELECT 
    dbo.fn_FormatarTempoMS(V.tempo) as tempo_formatado,
    P.nome as piloto,
    C.marca + ' ' + C.modelo as carro,
    Ev.nome as evento,
    V.tempo,
    S.data,
    V.id_volta,
    dbo.fn_FormatarTempoMS(dbo.fn_GapParaMelhor(V.id_volta)) as gap
FROM Volta V
INNER JOIN Piloto P ON V.numero_licenca = P.numero_licenca
INNER JOIN Carro C ON V.carro_VIN = C.VIN
INNER JOIN Sessao S ON V.id_sessao = S.id_sessao
INNER JOIN Evento Ev ON S.id_evento = Ev.id_evento;
GO

-- ==========================================
-- NOVAS STORED PROCEDURES
-- ==========================================

-- SP 1: Registar Utilizador com Role
CREATE PROCEDURE sp_RegistarUtilizador
    @username VARCHAR(50),
    @email VARCHAR(100),
    @password VARCHAR(64),
    @nome VARCHAR(100),
    @role VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        
        IF EXISTS (SELECT 1 FROM Utilizador WHERE username = @username)
        BEGIN
            RAISERROR('Username já existe', 16, 1);
            RETURN;
        END
        
        IF EXISTS (SELECT 1 FROM Utilizador WHERE email = @email)
        BEGIN
            RAISERROR('Email já existe', 16, 1);
            RETURN;
        END
        
        INSERT INTO Utilizador (username, email, password, nome)
        VALUES (@username, @email, @password, @nome);
        
        DECLARE @id_utilizador INT = SCOPE_IDENTITY();
        
        IF @role = 'tecnico_pista'
            INSERT INTO Tecnico_de_Pista (id_utilizador) VALUES (@id_utilizador);
        ELSE IF @role = 'diretor_equipa'
            INSERT INTO Diretor_de_Equipa (id_utilizador) VALUES (@id_utilizador);
        ELSE IF @role = 'diretor_corrida'
            INSERT INTO Diretor_de_Corrida (id_utilizador) VALUES (@id_utilizador);
        
        COMMIT TRANSACTION;
        SELECT @id_utilizador AS id_utilizador;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

-- SP 3: Alterar Status Evento
CREATE PROCEDURE sp_AlterarStatusEvento
    @id_evento INT,
    @novo_status VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        
        IF NOT EXISTS (SELECT 1 FROM Evento WHERE id_evento = @id_evento)
        BEGIN
            RAISERROR('Evento não encontrado', 16, 1);
            RETURN;
        END
        
        UPDATE Evento SET status = @novo_status WHERE id_evento = @id_evento;
        
        IF @novo_status = 'Concluído'
            UPDATE Sessao SET status = 'Concluída' WHERE id_evento = @id_evento;
        
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

-- SP 4: Alterar Status Sessão
CREATE PROCEDURE sp_AlterarStatusSessao
    @id_sessao INT,
    @novo_status VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    
    IF NOT EXISTS (SELECT 1 FROM Sessao WHERE id_sessao = @id_sessao)
    BEGIN
        RAISERROR('Sessão não encontrada', 16, 1);
        RETURN;
    END
    
    DECLARE @status_atual VARCHAR(20);
    SELECT @status_atual = ISNULL(status, 'Por Iniciar') FROM Sessao WHERE id_sessao = @id_sessao;
    
    IF @status_atual = 'Concluída' AND @novo_status != 'Concluída'
    BEGIN
        RAISERROR('Não é possível alterar status de sessão concluída', 16, 1);
        RETURN;
    END
    
    UPDATE Sessao SET status = @novo_status WHERE id_sessao = @id_sessao;
END;
GO

-- SP 5: Inscrever Equipa em Evento
CREATE PROCEDURE sp_InscreverEquipaEvento
    @id_equipa INT,
    @id_evento INT
AS
BEGIN
    SET NOCOUNT ON;
    
    IF EXISTS (SELECT 1 FROM Participa_Evento WHERE id_equipa = @id_equipa AND id_evento = @id_evento)
    BEGIN
        RAISERROR('Equipa já está inscrita neste evento', 16, 1);
        RETURN;
    END
    
    DECLARE @status VARCHAR(50);
    SELECT @status = status FROM Evento WHERE id_evento = @id_evento;
    
    IF @status NOT IN ('Por Iniciar', 'A Decorrer')
    BEGIN
        RAISERROR('Só é possível inscrever em eventos ativos', 16, 1);
        RETURN;
    END
    
    INSERT INTO Participa_Evento (id_equipa, id_evento) VALUES (@id_equipa, @id_evento);
END;
GO

-- SP 6: Cancelar Inscrição Evento
CREATE PROCEDURE sp_CancelarInscricaoEvento
    @id_equipa INT,
    @id_evento INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @count INT;
    SELECT @count = COUNT(*) 
    FROM Participa_Sessao ps
    INNER JOIN Sessao s ON ps.id_sessao = s.id_sessao
    INNER JOIN Piloto p ON ps.numero_licenca = p.numero_licenca
    WHERE s.id_evento = @id_evento AND p.id_equipa = @id_equipa;
    
    IF @count > 0
    BEGIN
        RAISERROR('Existem pilotos inscritos em sessões. Remova primeiro as inscrições.', 16, 1);
        RETURN;
    END
    
    DELETE FROM Participa_Evento WHERE id_equipa = @id_equipa AND id_evento = @id_evento;
END;
GO

-- SP 7: Inscrever em Sessão
CREATE PROCEDURE sp_InscreverSessao
    @id_sessao INT,
    @numero_licenca INT,
    @VIN_carro VARCHAR(50),
    @combustivel_inicial DECIMAL(5,2),
    @pressao_pneus DECIMAL(4,2),
    @configuracao_aerodinamica INT
AS
BEGIN
    SET NOCOUNT ON;
    
    IF EXISTS (SELECT 1 FROM Participa_Sessao WHERE id_sessao = @id_sessao AND numero_licenca = @numero_licenca)
    BEGIN
        RAISERROR('Este piloto já está inscrito nesta sessão', 16, 1);
        RETURN;
    END
    
    IF EXISTS (SELECT 1 FROM Participa_Sessao WHERE id_sessao = @id_sessao AND VIN_carro = @VIN_carro)
    BEGIN
        RAISERROR('Este carro já está inscrito nesta sessão', 16, 1);
        RETURN;
    END
    
    DECLARE @status VARCHAR(20);
    SELECT @status = ISNULL(status, 'Por Iniciar') FROM Sessao WHERE id_sessao = @id_sessao;
    
    IF @status = 'Concluída'
    BEGIN
        RAISERROR('Não é possível inscrever em sessão concluída', 16, 1);
        RETURN;
    END
    
    INSERT INTO Participa_Sessao (id_sessao, numero_licenca, VIN_carro, combustivel_inicial, pressao_pneus, configuracao_aerodinamica)
    VALUES (@id_sessao, @numero_licenca, @VIN_carro, @combustivel_inicial, @pressao_pneus, @configuracao_aerodinamica);
END;
GO

-- SP 8: Cancelar Inscrição Sessão
CREATE PROCEDURE sp_CancelarInscricaoSessao
    @id_sessao INT,
    @numero_licenca INT,
    @VIN_carro VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @status VARCHAR(20);
    SELECT @status = ISNULL(status, 'Por Iniciar') FROM Sessao WHERE id_sessao = @id_sessao;
    
    IF @status IN ('A Decorrer', 'Concluída')
    BEGIN
        RAISERROR('Não é possível desinscrever de sessão em andamento ou concluída', 16, 1);
        RETURN;
    END
    
    DELETE FROM Participa_Sessao 
    WHERE id_sessao = @id_sessao AND numero_licenca = @numero_licenca AND VIN_carro = @VIN_carro;
END;
GO

-- SP 9: Criar Equipa
CREATE PROCEDURE sp_CriarEquipa
    @nome VARCHAR(100),
    @pais VARCHAR(50),
    @id_utilizador_diretor INT
AS
BEGIN
    SET NOCOUNT ON;
    
    IF EXISTS (SELECT 1 FROM Equipa WHERE nome = @nome)
    BEGIN
        RAISERROR('Já existe uma equipa com este nome', 16, 1);
        RETURN;
    END
    
    IF EXISTS (SELECT 1 FROM Equipa WHERE ID_utilizador_diretor_de_equipa = @id_utilizador_diretor)
    BEGIN
        RAISERROR('Este diretor já possui uma equipa', 16, 1);
        RETURN;
    END
    
    INSERT INTO Equipa (nome, pais, ID_utilizador_diretor_de_equipa)
    VALUES (@nome, @pais, @id_utilizador_diretor);
    
    SELECT SCOPE_IDENTITY() AS id_equipa;
END;
GO

-- SP 10: Criar Sessão
CREATE PROCEDURE sp_CriarSessao
    @data DATE,
    @tipo VARCHAR(50),
    @hora_inicio TIME,
    @hora_fim TIME,
    @id_evento INT
AS
BEGIN
    SET NOCOUNT ON;
    
    IF NOT EXISTS (SELECT 1 FROM Evento WHERE id_evento = @id_evento)
    BEGIN
        RAISERROR('Evento não encontrado', 16, 1);
        RETURN;
    END
    
    IF @hora_fim <= @hora_inicio
    BEGIN
        RAISERROR('Hora fim deve ser maior que hora início', 16, 1);
        RETURN;
    END
    
    INSERT INTO Sessao (data, tipo, hora_inicio, hora_fim, id_evento, status)
    VALUES (@data, @tipo, @hora_inicio, @hora_fim, @id_evento, 'Por Iniciar');
    
    SELECT SCOPE_IDENTITY() AS id_sessao;
END;
GO

-- SP 11: Atualizar Evento
CREATE PROCEDURE sp_AtualizarEvento
    @id_evento INT,
    @nome VARCHAR(100),
    @tipo VARCHAR(50),
    @data_inicio DATE,
    @data_fim DATE,
    @status VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    
    IF NOT EXISTS (SELECT 1 FROM Evento WHERE id_evento = @id_evento)
    BEGIN
        RAISERROR('Evento não encontrado', 16, 1);
        RETURN;
    END
    
    IF @data_fim < @data_inicio
    BEGIN
        RAISERROR('Data fim deve ser >= data início', 16, 1);
        RETURN;
    END
    
    UPDATE Evento 
    SET nome = @nome, tipo = @tipo, data_inicio = @data_inicio, data_fim = @data_fim, status = @status
    WHERE id_evento = @id_evento;
END;
GO

-- SP 12: Atualizar Sessão
CREATE PROCEDURE sp_AtualizarSessao
    @id_sessao INT,
    @data DATE,
    @tipo VARCHAR(50),
    @hora_inicio TIME,
    @hora_fim TIME
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @status VARCHAR(20);
    SELECT @status = ISNULL(status, 'Por Iniciar') FROM Sessao WHERE id_sessao = @id_sessao;
    
    IF @status != 'Por Iniciar'
    BEGIN
        RAISERROR('Só é possível editar sessões com status "Por Iniciar"', 16, 1);
        RETURN;
    END
    
    UPDATE Sessao SET data = @data, tipo = @tipo, hora_inicio = @hora_inicio, hora_fim = @hora_fim
    WHERE id_sessao = @id_sessao;
END;
GO

-- SP 13: Remover Sessão
CREATE PROCEDURE sp_RemoverSessao
    @id_sessao INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @status VARCHAR(20);
    SELECT @status = ISNULL(status, 'Por Iniciar') FROM Sessao WHERE id_sessao = @id_sessao;
    
    IF @status IS NULL
    BEGIN
        RAISERROR('Sessão não encontrada', 16, 1);
        RETURN;
    END
    
    IF @status != 'Por Iniciar'
    BEGIN
        RAISERROR('Só é possível remover sessões com status "Por Iniciar"', 16, 1);
        RETURN;
    END
    
    DELETE FROM Sessao WHERE id_sessao = @id_sessao;
END;
GO

-- SP 14: Atualizar Condições Pista
CREATE PROCEDURE sp_AtualizarCondicoesPista
    @id_sessao INT,
    @temperatura_asfalto INT,
    @temperatura_ar INT,
    @humidade INT,
    @precipitacao INT
AS
BEGIN
    SET NOCOUNT ON;
    
    IF NOT EXISTS (SELECT 1 FROM Sessao WHERE id_sessao = @id_sessao)
    BEGIN
        RAISERROR('Sessão não encontrada', 16, 1);
        RETURN;
    END
    
    UPDATE Sessao 
    SET temperatura_asfalto = @temperatura_asfalto, temperatura_ar = @temperatura_ar,
        humidade = @humidade, precipitacao = @precipitacao
    WHERE id_sessao = @id_sessao;
END;
GO

-- SP 15: Atualizar Piloto
CREATE PROCEDURE sp_AtualizarPiloto
    @numero_licenca INT,
    @nome VARCHAR(100),
    @data_nascimento DATE,
    @nacionalidade VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE Piloto SET nome = @nome, data_nascimento = @data_nascimento, nacionalidade = @nacionalidade
    WHERE numero_licenca = @numero_licenca;
END;
GO

-- SP 16: Atualizar Carro
CREATE PROCEDURE sp_AtualizarCarro
    @VIN VARCHAR(50),
    @modelo VARCHAR(50),
    @marca VARCHAR(50),
    @categoria VARCHAR(30),
    @tipo_motor VARCHAR(30),
    @potencia INT,
    @peso INT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE Carro SET modelo = @modelo, marca = @marca, categoria = @categoria, 
        tipo_motor = @tipo_motor, potencia = @potencia, peso = @peso
    WHERE VIN = @VIN;
END;
GO

-- SP 17: Desvincular Piloto
CREATE PROCEDURE sp_DesvincularPiloto
    @numero_licenca INT,
    @id_equipa INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @count INT;
    SELECT @count = COUNT(*) FROM Participa_Evento pe
    INNER JOIN Evento e ON pe.id_evento = e.id_evento
    WHERE pe.id_equipa = @id_equipa AND e.status IN ('Por Iniciar', 'A Decorrer');
    
    IF @count > 0
    BEGIN
        RAISERROR('Não é possível remover pilotos enquanto equipa está em eventos ativos', 16, 1);
        RETURN;
    END
    
    UPDATE Piloto SET id_equipa = NULL WHERE numero_licenca = @numero_licenca AND id_equipa = @id_equipa;
END;
GO

-- SP 18: Desvincular Carro
CREATE PROCEDURE sp_DesvincularCarro
    @VIN VARCHAR(50),
    @id_equipa INT
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @count INT;
    SELECT @count = COUNT(*) FROM Participa_Evento pe
    INNER JOIN Evento e ON pe.id_evento = e.id_evento
    WHERE pe.id_equipa = @id_equipa AND e.status IN ('Por Iniciar', 'A Decorrer');
    
    IF @count > 0
    BEGIN
        RAISERROR('Não é possível remover carros enquanto equipa está em eventos ativos', 16, 1);
        RETURN;
    END
    
    UPDATE Carro SET id_equipa = NULL WHERE VIN = @VIN AND id_equipa = @id_equipa;
END;
GO