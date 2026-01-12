from ...extensions import db

class Conciliacao(db.Model):
    __tablename__ = 'tb_conciliacao'
    conc_reg = db.Column(db.Integer, primary_key=True)
    conc_banco_id = db.Column(db.Integer, db.ForeignKey('tb_banco.ban_reg'))
    conc_data = db.Column(db.Date)
    conc_descricao = db.Column(db.String(200))
    conc_valor = db.Column(db.Float)
    conc_tipo = db.Column(db.String(10))  # 'receita' ou 'despesa'
    conc_saldo_apos = db.Column(db.Float)
    
    banco = db.relationship('Banco')