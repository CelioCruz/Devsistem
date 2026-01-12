from ...extensions import db

class ContaPagar(db.Model):
    __tablename__ = 'tb_conta_pagar'
    cp_reg = db.Column(db.Integer, primary_key=True)
    cp_numero = db.Column(db.String(20))
    cp_data_vencimento = db.Column(db.Date)
    cp_data_emissao = db.Column(db.Date)
    cp_valor = db.Column(db.Float)
    cp_status = db.Column(db.String(20))
    cp_forma_pagamento = db.Column(db.String(50))