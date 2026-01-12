from ..extensions import db

class SaidaNF(db.Model):
    __tablename__ = 'tb_saida_nf'
    snf_reg = db.Column(db.Integer, primary_key=True)
    snf_numero = db.Column(db.String(20), unique=True)
    snf_chave = db.Column(db.String(44), unique=True)
    snf_cliente_id = db.Column(db.String(14), db.ForeignKey('tb_cliente.cli_cpf_cnpj'))
    snf_data_emissao = db.Column(db.DateTime)
    snf_valor_total = db.Column(db.Float)
    snf_status = db.Column(db.String(20), default='emitida')  # emitida, cancelada
    snf_xml = db.Column(db.Text)
    
    cliente = db.relationship('Cliente')