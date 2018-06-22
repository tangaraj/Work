# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError

class BankNameConfig(models.Model):
    _name = 'bank.name.config'
    _rec_name = 'name'

    name = fields.Char('Bank Name')
    bank_code = fields.Char('Bank Code')

    @api.one
    @api.constrains('name','bank_code')
    def _check_bank_name(self):
        if len(self.search([('name', '=ilike', self.name),('bank_code', '=ilike', self.bank_code)])) > 1:
            raise ValidationError('Bank name and code already exists')
        if len(self.search([('name', '=ilike', self.name)])) > 1:
            raise ValidationError('Bank Name already exists')
        if len(self.search([('bank_code', '=ilike', self.bank_code)])) > 1:
            raise ValidationError('Bank Code already exists')