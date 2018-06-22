# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
import time
from datetime import datetime

class BankStatus(models.Model):
    _name = 'bank.status'
    _rec_name = 'payment_mode'

    @api.model
    def _default_society(self):
        user_id = self.env['res.users'].sudo().browse(self.env.uid)
        if len(user_id.company_id.parent_id) > 0 and user_id.company_id.parent_id.type == 'society':
            return user_id.company_id.parent_id.id
        elif user_id.company_id.type == 'society':
            return user_id.company_id.id

    @api.model
    def _default_school(self):
        user_id = self.env['res.users'].sudo().browse(self.env.uid)
        if user_id.company_id and user_id.company_id.type == 'school':
            return user_id.company_id.id

    society_id = fields.Many2one('res.company', string='Society', default=_default_society)
    school_id = fields.Many2one('res.company', string='School', default=_default_school)
    academic_year_id = fields.Many2one('academic.year',string='Academic Year')
    payment_mode = fields.Selection([('cheque/dd', 'Cheque'),('dd','DD'),('card', 'PoS')], string='Payment Mode')
    bank_status = fields.Selection([('cleared', 'Cleared'), ('uncleared', 'Uncleared')], string='Status by Bank', default='uncleared')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    cheque_ids = fields.One2many('pappaya.fees.receipt','bank_id',string='Cheque')
    dd_ids = fields.One2many('pappaya.fees.receipt','bank_id',string='DD')
    pos_ids = fields.One2many('pappaya.fees.receipt','bank_id',string='POS')
    cleared_amt = fields.Float(string='Cleared Amount', compute='compute_amount', store=True)
    uncleared_amt = fields.Float(string='Uncleared Amount', compute='compute_amount', store=True)
    total_amt = fields.Float(string='Total Amount', compute='compute_amount', store=True)
    created_on = fields.Datetime(string='Created On', default=lambda self: fields.Datetime.now())
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)

    @api.one
    @api.constrains('from_date','to_date')
    def _check_date(self):
        if len(self.search([('society_id','=',self.society_id.id),('school_id','=',self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('payment_mode', '=', self.payment_mode),('bank_status', '=', self.bank_status),('from_date', '<=', self.from_date),('to_date', '>=', self.to_date)]).ids) > 1:
            raise ValidationError('Record already exists')
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValidationError('To Date must be greater than From Date')
        if self.to_date and self.to_date > time.strftime('%Y-%m-%d'):
            raise ValidationError('To Date is in the future!')
        mode_dict = {'cheque/dd': 'Cheque', 'dd': 'DD', 'card': 'PoS'}
        fee_obj = self.env['pappaya.fees.receipt'].search([('society_id', '=', self.society_id.id), ('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id), ('payment_mode', 'in', ['cheque/dd', 'card', 'dd']),('receipt_date', '>=', self.from_date), ('receipt_date', '<=', self.to_date)])
        if self.society_id and self.school_id and self.academic_year_id and self.payment_mode and self.bank_status and self.from_date and self.to_date and not fee_obj:
            raise ValidationError("%s details are unavailable for the selected date range" % (mode_dict[self.payment_mode]))

    @api.onchange('society_id')
    def onchange_society_id(self):
        if self.society_id:
            self.school_id = None
            self.academic_year_id = None
            self.payment_mode = None
            self.bank_status = 'uncleared'
            self.from_date = None
            self.to_date = None
            self.cheque_ids = None
            self.dd_ids = None
            self.pos_ids = None
            self.total_amt = 0.0
            self.cleared_amt = 0.0
            self.uncleared_amt = 0.0

    @api.onchange('school_id')
    def onchange_school_id(self):
        if self.school_id:
            self.academic_year_id = None
            self.payment_mode = None
            self.bank_status = 'uncleared'
            self.from_date = None
            self.to_date = None
            self.cheque_ids = None
            self.dd_ids = None
            self.pos_ids = None
            self.total_amt = 0.0
            self.cleared_amt = 0.0
            self.uncleared_amt = 0.0

    @api.onchange('academic_year_id')
    def onchange_academic_year(self):
        if self.academic_year_id:
            self.payment_mode = None
            self.bank_status = 'uncleared'
            self.from_date = None
            self.to_date = None
            self.cheque_ids = None
            self.dd_ids = None
            self.pos_ids = None
            self.total_amt = 0.0
            self.cleared_amt = 0.0
            self.uncleared_amt = 0.0

    @api.onchange('payment_mode')
    def onchange_payment_mode(self):
        if self.payment_mode:
            self.bank_status = 'uncleared'
            self.from_date = None
            self.to_date = None
            self.cheque_ids = None
            self.dd_ids = None
            self.pos_ids = None
            self.total_amt = 0.0
            self.cleared_amt = 0.0
            self.uncleared_amt = 0.0

    @api.onchange('bank_status')
    def onchange_bank_status(self):
        if self.bank_status:
            self.from_date = None
            self.to_date = None
            self.cheque_ids = None
            self.dd_ids = None
            self.pos_ids = None
            self.total_amt = 0.0
            self.cleared_amt = 0.0
            self.uncleared_amt = 0.0

    @api.onchange('from_date')
    def onchange_from_date(self):
        if self.from_date:
            self.to_date = None
            self.cheque_ids = None
            self.dd_ids = None
            self.pos_ids = None
            self.total_amt = 0.0
            self.cleared_amt = 0.0
            self.uncleared_amt = 0.0

    @api.onchange('to_date')
    def onchange_date(self):
        self.cheque_ids = self.dd_ids = self.pos_ids = None
        self.total_amt = self.cleared_amt = self.uncleared_amt =  0.0

        if self.to_date and self.to_date > time.strftime('%Y-%m-%d'):
            raise ValidationError('To Date is in the future!')

        mode_dict = {'cheque/dd': 'Cheque', 'dd': 'DD', 'card': 'PoS'}
        fee_obj = self.env['pappaya.fees.receipt'].search([('society_id', '=', self.society_id.id), ('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('payment_mode', 'in', ['cheque/dd','card','dd']),('receipt_date', '>=', self.from_date),('receipt_date', '<=', self.to_date)])

        if self.society_id and self.school_id and self.academic_year_id and self.payment_mode and self.bank_status and self.from_date and self.to_date:
            if not fee_obj:
                raise ValidationError("%s details are unavailable for the selected date range" % (mode_dict[self.payment_mode]))
            cheque_list, dd_list, pos_list = [], [], []
            for obj in self.env['pappaya.fees.receipt'].search([('society_id', '=', self.society_id.id), ('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('receipt_date', '>=', self.from_date),('receipt_date', '<=', self.to_date)]):
                if obj.payment_mode == 'cheque/dd' and self.payment_mode == 'cheque/dd':
                    if obj.receipt_status == 'cleared' and self.bank_status in ['cleared']:
                        cheque_list.append(obj.id)
                    if obj.receipt_status == 'uncleared' and self.bank_status in ['uncleared']:
                        cheque_list.append(obj.id)
                    if obj.receipt_status not in ['cleared', 'uncleared'] and self.bank_status in ['uncleared']:
                        cheque_list.append(obj.id)
                if obj.payment_mode == 'dd' and self.payment_mode == 'dd':
                    if obj.receipt_status == 'cleared' and self.bank_status in ['cleared']:
                        dd_list.append(obj.id)
                    if obj.receipt_status == 'uncleared' and self.bank_status in ['uncleared']:
                        dd_list.append(obj.id)
                    if obj.receipt_status not in ['cleared', 'uncleared'] and self.bank_status in ['uncleared']:
                        dd_list.append(obj.id)
                if obj.payment_mode == 'card' and self.payment_mode == 'card':
                    if obj.receipt_status == 'cleared' and self.bank_status in ['cleared']:
                        pos_list.append(obj.id)
                    if obj.receipt_status == 'uncleared' and self.bank_status in ['uncleared']:
                        pos_list.append(obj.id)
                    if obj.receipt_status not in ['cleared','uncleared'] and self.bank_status in ['uncleared']:
                        pos_list.append(obj.id)
            exist_cheque_list = []
            for record in self.search([('society_id', '=', self.society_id.id), ('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('payment_mode', '=', 'cheque/dd')]):
                for cheque in record.cheque_ids:
                    if record.bank_status == 'cleared' and self.bank_status in ['cleared']:
                        exist_cheque_list.append(cheque.id)
                    if record.bank_status == 'uncleared' and self.bank_status in ['uncleared']:
                        exist_cheque_list.append(cheque.id)
                    if record.bank_status not in ['cleared', 'uncleared'] and self.bank_status in ['uncleared']:
                        exist_cheque_list.append(cheque.id)
            new_cheque_list = list(set(cheque_list) - set(exist_cheque_list))
            self.cheque_ids = [(6, 0, new_cheque_list)]
            exist_dd_list = []
            for record in self.search([('society_id', '=', self.society_id.id), ('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('payment_mode', '=', 'dd')]):
                for dd in record.dd_ids:
                    if record.bank_status == 'cleared' and self.bank_status in ['cleared']:
                        exist_dd_list.append(dd.id)
                    if record.bank_status == 'uncleared' and self.bank_status in ['uncleared']:
                        exist_dd_list.append(dd.id)
                    if record.bank_status not in ['cleared', 'uncleared'] and self.bank_status in ['uncleared']:
                        exist_dd_list.append(dd.id)
            new_dd_list = list(set(dd_list) - set(exist_dd_list))
            self.dd_ids = [(6, 0, new_dd_list)]
            exist_pos_list = []
            for record in self.search([('society_id', '=', self.society_id.id), ('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id), ('payment_mode', '=', 'pos')]):
                for pos in record.pos_ids:
                    if record.bank_status == 'cleared' and self.bank_status in ['cleared']:
                        exist_pos_list.append(pos.id)
                    if record.bank_status == 'uncleared' and self.bank_status in ['uncleared']:
                        exist_pos_list.append(pos.id)
                    if record.bank_status not in ['cleared', 'uncleared'] and self.bank_status in ['uncleared']:
                        exist_pos_list.append(pos.id)
            new_pos_list = list(set(pos_list) - set(exist_pos_list))
            self.pos_ids = [(6, 0, new_pos_list)]

    @api.depends('cheque_ids.total','dd_ids.total','pos_ids.total','cheque_ids.receipt_status','dd_ids.receipt_status','pos_ids.receipt_status')
    def compute_amount(self):
        for rec in self:
            clr,unclr = 0.0,0.0
            if rec.cheque_ids:
                for line in rec.cheque_ids:
                    if line.payment_mode =='cheque/dd' and rec.payment_mode == 'cheque/dd':
                        rec.total_amt = sum(line.total for line in rec.cheque_ids)
                    if line.payment_mode =='cheque/dd' and rec.payment_mode == 'cheque/dd' and line.is_select == True and line.receipt_status == 'cleared':
                        clr += line.total
                    if line.payment_mode =='cheque/dd' and rec.payment_mode == 'cheque/dd' and line.is_select == False and line.receipt_status == 'uncleared':
                        unclr += line.total
                rec.cleared_amt = clr
                rec.uncleared_amt = unclr
            if rec.dd_ids:
                for line in rec.dd_ids:
                    if line.payment_mode == 'dd' and rec.payment_mode == 'dd':
                        rec.total_amt = sum(line.total for line in rec.dd_ids)
                    if line.payment_mode == 'dd' and rec.payment_mode == 'dd' and line.is_select == True and line.receipt_status == 'cleared':
                        clr += line.total
                    if line.payment_mode == 'dd' and rec.payment_mode == 'dd' and line.is_select == False and line.receipt_status == 'uncleared':
                        unclr += line.total
                rec.cleared_amt = clr
                rec.uncleared_amt = unclr
            if rec.pos_ids:
                for line in rec.pos_ids:
                    if line.payment_mode =='card' and rec.payment_mode == 'card':
                        rec.total_amt = sum(line.total for line in rec.pos_ids)
                    if line.payment_mode =='card' and rec.payment_mode == 'card' and line.is_select == True and line.receipt_status == 'cleared':
                        clr += line.total
                    if line.payment_mode =='card' and rec.payment_mode == 'card' and line.is_select == False and line.receipt_status == 'uncleared':
                        unclr += line.total
                rec.cleared_amt = clr
                rec.uncleared_amt = unclr

    @api.multi
    def action_cleared(self):
        for rec in self:
            if rec.cheque_ids:
                if all(line.is_select == False for line in rec.cheque_ids):
                    raise ValidationError('Please select the record to proceed')
                for line in rec.cheque_ids:
                    if line.is_select == True:
                        line.write({'receipt_status':'cleared'})
            if rec.dd_ids:
                if all(line.is_select == False for line in rec.dd_ids):
                    raise ValidationError('Please select the record to proceed')
                for line in rec.dd_ids:
                    if line.is_select == True:
                        line.write({'receipt_status':'cleared'})
            if rec.pos_ids:
                if all(line.is_select == False for line in rec.pos_ids):
                    raise ValidationError('Please select the record to proceed')
                for line in rec.pos_ids:
                    if line.is_select == True:
                        line.write({'receipt_status':'cleared'})
