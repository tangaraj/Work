# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
from datetime import datetime


class papaya_employee_benefit(models.Model):
    _name = 'pappaya.employee.benefit'

    name=fields.Char('Name')
    amount = fields.Integer('Amount')
    dept_id = fields.Many2one('hr.department', 'Department')


class hr_department_inherit(models.Model):
    _inherit = 'hr.department'

    benefit_o2m = fields.One2many('pappaya.employee.benefit','dept_id', 'Benefits')
