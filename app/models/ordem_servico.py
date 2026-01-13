from datetime import datetime
from ..extensions import db

class OrdemServico(db.Model):
    __tablename__ = 'ordem_servico'
    
    os_numero = db.Column(db.String(7), primary_key=True)
    cv_numero = db.Column(db.Integer, nullable=False)
    loja_id = db.Column(db.String(2), nullable=False)
    cliente_id = db.Column(db.Integer)  
    fornecedor_id = db.Column(db.Integer) 
    numero_pedido_fornecedor = db.Column(db.String(50))
    status = db.Column(db.String(50), default='venda_concluida')
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    observacao_devolucao = db.Column(db.Text)
    data_alerta_armação = db.Column(db.DateTime)
    data_leitura_alerta = db.Column(db.DateTime)
    usuario_leitura_id = db.Column(db.Integer)
    qtd_reprocessamentos = db.Column(db.Integer, default=0)