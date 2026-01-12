from . import db
from datetime import datetime, date

class Caixa(db.Model):
    __tablename__ = 'caixa'
    
    cai_reg = db.Column(db.Integer, primary_key=True)
    cai_data = db.Column(db.Date, default=date.today)
    cai_loja = db.Column(db.String(2), nullable=False)
    cai_usuario_abertura = db.Column(db.Integer)  # ID do usuário
    cai_usuario_fechamento = db.Column(db.Integer)    
    
    cai_saldo_inicial = db.Column(db.Numeric(10, 2), default=0.0)
    cai_hora_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    cai_saldo_final = db.Column(db.Numeric(10, 2), default=0.0)
    cai_hora_fechamento = db.Column(db.DateTime)
    cai_retiradas = db.Column(db.Numeric(10, 2), default=0.0)
    cai_suprimentos = db.Column(db.Numeric(10, 2), default=0.0)
    cai_observacao = db.Column(db.Text)
    cai_status = db.Column(db.String(20), default='fechado') 

    # Formas de pagamento (fechamento)
    cai_dinheiro_caixa = db.Column(db.Numeric(10, 2), default=0.0)
    cai_dinheiro_retrada = db.Column(db.Numeric(10, 2), default=0.0)
    cai_cheque_caixa = db.Column(db.Numeric(10, 2), default=0.0)
    cai_pix_caixa = db.Column(db.Numeric(10, 2), default=0.0)
    cai_cartao_caixa = db.Column(db.Numeric(10, 2), default=0.0)
    # ... outros campos ...

    cai_total_conferencia = db.Column(db.Numeric(10, 2), default=0.0)
    cai_total_sistema = db.Column(db.Numeric(10, 2), default=0.0)
    cai_falta = db.Column(db.Numeric(10, 2), default=0.0)
    cai_malote = db.Column(db.Numeric(10, 2), default=0.0)

    # 💳 Transferências
    cai_transferido_empresa = db.Column(db.Boolean, default=False)  # fechamento parcial
    cai_transferido_tesouraria = db.Column(db.Boolean, default=False)  # finalização do dia
    cai_data_transferencia_empresa = db.Column(db.DateTime)
    cai_data_transferencia_tesouraria = db.Column(db.DateTime)