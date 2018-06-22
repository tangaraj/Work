# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
import time
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class BankDeposit(models.Model):
    _name = 'bank.deposit'
    _rec_name = 'academic_year_id'


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

    state = fields.Selection([('draft', 'In hand'),('requested', 'Requested'), ('approved', 'Approved'), ('rejected', 'Rejected')], 'Status', default='draft')
    society_id = fields.Many2one('res.company', string='Society',default=_default_society)
    school_id = fields.Many2one('res.company', string='School',default=_default_school)
    academic_year_id = fields.Many2one('academic.year', string='Academic Year')
    bank_id = fields.Many2one('bank.account.config', string='Bank Account Name')
    payment_mode = fields.Selection([('cash','Cash'),('cheque/dd','Cheque'),('dd','DD'),('card','PoS'),('neft/rtgs', 'NEFT/RTGS')],string='Payment Mode')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    deposit_date = fields.Date(string='Date of Deposit')
    approve_date = fields.Date(string='Date of Approved')
    # Cash
    cash_receipt_ids = fields.Many2many('pappaya.fees.receipt', 'cash_deposit_fees_receipt_rel', 'cash_id', 'receipt_id', string='Cash')
    opening_bal = fields.Float(string='Opening Balance')
    closing_bal = fields.Float(string='Closing Balance')
    total_cash_amt = fields.Float(string='Collection Amount')
    c_amt_deposit = fields.Float(string='Amount Deposited')
    c_bank_id = fields.Many2one('bank.account.config', string='Deposited Bank')
    c_ref_no = fields.Char(string='Cheque/DD/PoS')
    #c_pay_slip = fields.Many2many('ir.attachment', string="Pay Slip")
    c_pay_slip = fields.Binary(string="Pay Slip")
    file_name = fields.Char('File Name')
    
    total_amt_deposited = fields.Float(string='Total Amount Deposited')
    grand_total = fields.Float(string='Grand Total',readonly="1")
    total_cheque_pos_amt = fields.Float(string='Total Amount')
    cleared_amt = fields.Float(string='Cleared Amount')
    uncleared_amt = fields.Float(string='Uncleared Amount')
    remarks = fields.Text(string='Remarks')
    created_on = fields.Datetime(string='Created On', default=lambda self: fields.Datetime.now())
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    # Fiscal Year
    is_fiscal_year = fields.Boolean(string='Is Fiscal Year?',default=False)
    fiscal_ob = fields.Float(string='Fiscal Opening Balance')
    is_updated = fields.Boolean(string='Update')
    previous_deposit_id = fields.Many2one('bank.deposit')
    cancel_remarks = fields.Text(string="Cancel Receipt Details")
    canceld_amt = fields.Char

    
    @api.multi
    def update_ob(self):
        if self.is_fiscal_year == True and self.fiscal_ob == 0.0:
            raise ValidationError('Please update the fiscal year opening balance')
        if self.is_fiscal_year == True and self.fiscal_ob > 0.0:
            self.write({'opening_bal':self.fiscal_ob,'is_updated':True})

    @api.onchange('society_id')
    def onchange_society_id(self):
        if self.society_id:
            self.academic_year_id = None
    

    

    @api.onchange('school_id')
    def onchange_school_id(self):
        self.academic_year_id = None
        if self.school_id:
            self.academic_year_id = self.deposit_date = self.cash_receipt_ids = self.opening_bal = self.closing_bal = self.c_amt_deposit = self.c_ref_no = self.c_pay_slip = None
            bank_name = self.env['bank.account.config'].search([('society_id', '=', self.society_id.id),('school_ids','in',self.school_id.id)], limit=1)
            self.bank_id = bank_name.id
            return {'domain': {
                'bank_id': [('society_id', '=', self.society_id.id), ('school_ids', 'in', self.school_id.id)],
                'c_bank_id': [('society_id', '=', self.society_id.id), ('school_ids', 'in', self.school_id.id)],
                }}

    @api.onchange('deposit_date')
    def onchange_deposit_date(self):
        if self.deposit_date and self.deposit_date > time.strftime('%Y-%m-%d'):
            raise ValidationError('Date of Deposit is in the future!')
        


    @api.onchange('academic_year_id')
    def onchange_receipt(self):
        self.cash_receipt_ids = None
        self.opening_bal = self.closing_bal = self.c_amt_deposit = self.c_ref_no = self.c_pay_slip = None
        
        exist_cash_list = []
        for record in self.search([('society_id', '=', self.society_id.id), ('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('state', '!=','rejected')]):
            for cash in record.cash_receipt_ids:
                exist_cash_list.append(cash.id)
        
        
        ob_ids = self.search([('society_id','=',self.society_id.id),('school_id','=',self.school_id.id),('academic_year_id','=',self.academic_year_id.id),('state', '!=','rejected'),],order = "id desc", limit=1)
        if ob_ids:
            for ob in ob_ids[0]:
                self.opening_bal = ob.closing_bal
                self.previous_deposit_id = ob.id
            
        fee_obj = self.env['pappaya.fees.receipt'].sudo().search([('society_id', '=', self.society_id.id),('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('id', 'not in', exist_cash_list),('receipt_status','=','cleared'),('state','not in',['refund','cancel'])])
#         if self.society_id and self.school_id and self.academic_year_id and not fee_obj:
#             raise ValidationError("Details are unavailable for the selected academic year")
        
        if self.society_id and self.school_id and self.academic_year_id :
            cash_list = []
            obj = self.env['pappaya.fees.receipt'].sudo().search([('society_id', '=', self.society_id.id),('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('id', 'not in', exist_cash_list),('payment_mode','=','cash'),('receipt_status','=','cleared'),('state','not in',['refund','cancel'])])
            self.cash_receipt_ids = [(6, 0, obj.ids)]
            cash_total = 0.0
            for line in self.cash_receipt_ids:
                cash_total += line.total
            self.grand_total = cash_total
            self.total_cash_amt = cash_total
            self.closing_bal = self.opening_bal + self.total_cash_amt
    
    
    @api.model
    def create(self, vals):
        res = super(BankDeposit, self).create(vals)
        cash_total = 0.0
        if res.cash_receipt_ids:
           for line in res.cash_receipt_ids:
                cash_total += line.total

        opening_amount = 0.0
        if res.previous_deposit_id.closing_bal: 
            opening_amount = res.previous_deposit_id.closing_bal
        else:
            opening_amount = res.opening_bal 
        if not (res.fiscal_ob and res.is_fiscal_year):
            res['opening_bal'] = opening_amount
            res['total_cash_amt'] = cash_total
            res['grand_total'] = cash_total
            res['closing_bal'] = res['opening_bal'] + res['total_cash_amt']
        return res
    
    @api.multi
    def action_draft_request(self):
        if self.c_amt_deposit <= 0.0:
            raise ValidationError(_("Please enter Deposit Amount.!"))

        
        for rec in self:
            if rec.state != 'approved':
                opening_amount = 0.0
                cash_total = 0.0
                if rec.previous_deposit_id.closing_bal: 
                    opening_amount = rec.previous_deposit_id.closing_bal
                else:
                    opening_amount = rec.opening_bal 
                if not (rec.fiscal_ob and rec.is_fiscal_year):
                    #if rec.previous_deposit_id:
                    rec.opening_bal = opening_amount
                for line in rec.cash_receipt_ids:
                        cash_total += line.total
                rec.total_cash_amt = cash_total
                rec.grand_total = cash_total
                rec.total_amt_deposited = rec.c_amt_deposit
                rec.closing_bal = rec.opening_bal + rec.total_cash_amt
            else:
                cash_total = 0.0
                for line in rec.cash_receipt_ids:
                        cash_total += line.total
                rec.grand_total = cash_total
                rec.total_amt_deposited = cash_total
                
        self.write({'state': 'requested'})
        
        
    @api.multi
    def action_request_approve(self):
        for rec in self:
            opening_amount = 0.0
            if rec.previous_deposit_id.closing_bal: 
                opening_amount = rec.previous_deposit_id.closing_bal
            else:
                opening_amount = rec.opening_bal
            rec.sudo().write({'total_amt_deposited':rec.c_amt_deposit,'closing_bal':opening_amount + rec.total_cash_amt - rec.c_amt_deposit,'opening_bal':opening_amount})
            parent_id_exists = True
            next_id = self.sudo().search([('previous_deposit_id', '=', rec.id)])
            if next_id:
                for next in next_id:
                    opening_amount = 0.0
                    if next.previous_deposit_id.closing_bal: 
                        opening_amount = next.previous_deposit_id.closing_bal
                    else:
                        opening_amount = next.opening_bal
                    if next.state == 'approved':
                        next.sudo().write({'total_amt_deposited':opening_amount + next.total_cash_amt - next.c_amt_deposit,'opening_bal':opening_amount})
                    else:
                        next.sudo().write({'total_amt_deposited':next.c_amt_deposit,'closing_bal':opening_amount + next.total_cash_amt,'opening_bal':opening_amount})
                n_next_id = self.sudo().search([('previous_deposit_id', '=', next.id)])
                if not n_next_id:
                    parent_id_exists = False
                while parent_id_exists:
                    for next in n_next_id:
                        if next.previous_deposit_id.closing_bal: 
                            opening_amount = next.previous_deposit_id.closing_bal
                        else:
                            opening_amount = next.opening_bal
                        if next.state == 'approved':
                            next.sudo().write({'total_amt_deposited':next.c_amt_deposit,'closing_bal':opening_amount + next.total_cash_amt - next.c_amt_deposit,'opening_bal':opening_amount})
                        else:
                            next.sudo().write({'total_amt_deposited':next.c_amt_deposit,'closing_bal':opening_amount + next.total_cash_amt,'opening_bal':opening_amount})
                    nn_next_id = self.sudo().search([('previous_deposit_id', '=', next.id)])
                    if not nn_next_id: 
                        parent_id_exists = False
            self.write({'state': 'approved','approve_date':datetime.now().date()})            

    @api.multi
    def action_request_reject(self):

        self.write({'state': 'rejected'})
        
