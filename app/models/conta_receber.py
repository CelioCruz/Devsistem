from ...extensions import db

class ContaReceber(db.Model):
    __tablename__ = 'tb_conta_receber'
    cr_reg = db.Column(db.Integer, primary_key=True)
    cr_numero = db.Column(db.String(20))
    cr_data_vencimento = db.Column(db.Date)
    cr_data_emissao = db.Column(db.Date)
    cr_valor = db.Column(db.Float)
    cr_status = db.Column(db.String(20))
    cr_forma_pagamento = db.Column(db.String(50))