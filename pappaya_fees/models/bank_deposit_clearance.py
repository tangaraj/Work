# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
import time
from datetime import datetime

class bank_deposit_clearance(models.Model):
    _name = 'bank.deposit.clearance'
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
    payment_mode = fields.Selection([('cheque/dd', 'Cheque'),('dd','DD'),('card', 'PoS'),('neft/rtgs','Neft/RTGS')], string='Payment Mode')
    status = fields.Selection([('draft', 'In hand'),('deposit','Deposited')], string='Status', default='draft')
    payment_line_status = fields.Selection([('uncleared','Uncleared'),('cleared','Cleared')], string='Status', default='cleared')
    line_ids = fields.One2many('bank.deposit.clearance.line','bank_clearance_id',string='Bank Deposit Clearance Line')
    status_line_ids = fields.One2many('payment.status.line','bank_clearance_id',string='Payment Status Line')
    total_amt = fields.Float(compute='compute_total_amt', string="Total")
    read_only = fields.Boolean(string="Read Only?")
    cleared_amt = fields.Float(compute='compute_total_amt', string="Cleared Amount")
    c_bank_id = fields.Many2one('bank.account.config', string='Deposited Bank')
    uncleared_amt = fields.Float(compute='compute_total_amt', string="Uncleared Amount")
    rejected_amt = fields.Float(compute='compute_total_amt', string="Rejected Amount")
    created_on = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now())
    confirm_on = fields.Date(string='Date')
    cleared_date = fields.Date(string='Date of Cleared')
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    remarks = fields.Text(string='Remarks')
    
          
    
    @api.onchange('society_id')
    def onchange_society_id(self):
        if self.society_id:
            self.academic_year_id = None
            self.payment_mode = None
            self.line_ids = None
    
#     @api.constrains('line_ids')
#     def check_line_ids(self):
#         is_select = [ref for ref in self.line_ids.mapped('is_select') if ref]
#         if not is_select:
#             raise ValidationError(_("Please select the record"))
        
                    
    @api.multi
    def confirm(self):
        is_select = [ref for ref in self.line_ids.mapped('is_select') if ref]
        if not is_select:
            raise ValidationError(_("Please select the record"))
        line_list = []
        for line in self.line_ids:
            if line.is_select:
                line_list.append((0,0,{
                                    'receipt_id':line.receipt_id.id, 
                                    'is_select':False,
                                    'name':line.name, 
                                    'enrollment_number':line.enrollment_number, 
                                    'grade_id':line.grade_id.id, 
                                    'student_id': line.student_id.id,
                                    'receipt_date':line.receipt_date, 
                                    'payment_mode': line.payment_mode,
                                    'cheque_dd': line.cheque_dd,
                                    'total':line.total,
                                    'state':'uncleared',
                                    'status':'uncleared',
                                    'attachment':line.attachment,
                                    'file_name':line.file_name
                                }))
                line.write({'state':'deposit','read_only':True})
                
            else:
                line.sudo().unlink()
        if line_list:
            self.status_line_ids = line_list
        self.write({'payment_line_status':'uncleared','status':'deposit','read_only':True,'confirm_on':datetime.now().date()})
    
    @api.multi
    def confirm_cleared(self):
        all_receipt_uncleared = False
        for line in self.status_line_ids:
            if line.is_select and line.state == 'uncleared':
                line.receipt_id.write({'receipt_status':'cleared'})
                line.write({'state':'cleared','read_only':True})
                all_receipt_uncleared = False
            else:
                all_receipt_uncleared = True
        if not all_receipt_uncleared:
            self.write({'payment_line_status':'cleared','cleared_date':datetime.now().date()})
            
    @api.multi
    def confirm_rejected(self):
        all_receipt_uncleared = False
        for line in self.status_line_ids:
            if line.is_select and line.state == 'uncleared':
                #line.receipt_id.write({'receipt_status':'cleared'})
                if line.receipt_id.fee_collection_id:
                    for receipt_line in line.receipt_id.fees_receipt_line:
                        for collection_line in line.receipt_id.fee_collection_id.fees_collection_line:
                            if receipt_line.name == collection_line.name:
                                if collection_line.total_paid == receipt_line.amount:
                                    collection_line.write({'due_amount':(collection_line.due_amount + receipt_line.amount),
                                                           'total_paid':(collection_line.total_paid - receipt_line.amount),
                                                           'pay':False,
                                                           'term_state':'due' })
                        fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id', '=', line.receipt_id.fee_collection_id.id)]) 
                        if fees_ledger:
                            for ledger in  fees_ledger:
                                if ledger.fee_ledger_line:
                                    for ledger_line in ledger.fee_ledger_line:
                                        if ledger_line.name ==  receipt_line.name:
                                            ledger_line.write({
                                                'debit':ledger_line.debit - receipt_line.amount,
                                                'balance':ledger_line.balance + receipt_line.amount
                                                })
                                if ledger.fee_receipt_ledger_line:
                                    for ledger_receipt_line in ledger.fee_receipt_ledger_line:
                                        if ledger_receipt_line.fees_receipt_id.id == line.receipt_id.id and line.receipt_id.name == ledger_receipt_line.fees_receipt_id.name:
                                            
                                            if ledger_receipt_line.fees_head ==  receipt_line.name:
                                                ledger_receipt_line.write({'transaction':str(ledger_receipt_line.transaction) + ' ' + 'Receipt Rejected' })
                line.receipt_id.write({'state':'cancel'})
                
                line.write({'state':'rejected','read_only':True})
                all_receipt_uncleared = False
            else:
                all_receipt_uncleared = True
        if not all_receipt_uncleared:
            self.write({'payment_line_status':'cleared','cleared_date':datetime.now().date()})
    
    @api.onchange('payment_mode')
    def onchange_payment_mode(self):
        exist_list = []
        reject_list = []
        self.line_ids = None
        for record in self.search([('society_id', '=', self.society_id.id), ('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('payment_mode','=', self.payment_mode),('status','=', 'deposit')]):
            for line in record.line_ids:
                if line.is_select: 
                    exist_list.append(line.receipt_id.id)
                    
            for line in record.status_line_ids:
                if line.is_select and line.state == 'rejected' and line.receipt_id.receipt_status == 'uncleared':
                    reject_list.append(line.receipt_id.id)
        for reject in reject_list:
            exist_list.remove(reject)
            
        fee_obj = self.env['pappaya.fees.receipt'].sudo().search([('society_id', '=', self.society_id.id),('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('id', 'not in', exist_list),('payment_mode','=', self.payment_mode),('receipt_status', '=', 'uncleared'),('state','not in',['refund','cancel'])])
        if self.society_id and self.school_id and self.academic_year_id and not fee_obj:
            raise ValidationError("Details are unavailable for the selected academic year")
        
        if self.society_id and self.school_id and self.academic_year_id :
            cash_list = []
            receipt_obj = self.env['pappaya.fees.receipt'].sudo().search([('society_id', '=', self.society_id.id),('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id),('id', 'not in', exist_list),('payment_mode','=', self.payment_mode),('receipt_status', '=', 'uncleared'),('state','not in',['refund','cancel'])])
            receipt_list = []
            for receipt_line in receipt_obj:
                receipt_list.append((0,0,{
                                        'receipt_id':receipt_line.id, 
                                        'is_select':False,
                                        'name':receipt_line.name, 
                                        'enrollment_number':receipt_line.enrollment_number, 
                                        'grade_id':receipt_line.grade_id.id, 
                                        'student_id': receipt_line.student_id.id,
                                        'receipt_date':receipt_line.receipt_date, 
                                        'payment_mode': receipt_line.payment_mode,
                                        'cheque_dd': receipt_line.cheque_dd,
                                        'total':receipt_line.total,
                                        'receipt_status': receipt_line.receipt_status,
                                        'state':'draft'
                                    }))
            self.line_ids = receipt_list    
    @api.one
    @api.depends('status_line_ids')
    def compute_total_amt(self):
        cleared_total,uncleared_total,rejected_total,total = 0.0,0.0,0.0,0.0
        if self.status_line_ids:
            for rec in self.status_line_ids:
                if rec.state =='uncleared':
                    uncleared_total+= rec.total
                if rec.state =='cleared':
                    cleared_total+= rec.total
                if rec.state == 'rejected':
                    rejected_total += rec.total
                total+=rec.total
        self.cleared_amt = cleared_total
        self.uncleared_amt = uncleared_total
        self.rejected_amt = rejected_total
        self.total_amt = total
        
    
    
class Bank_Deposit_Clearance_Line(models.Model):
    _name = 'bank.deposit.clearance.line'

    receipt_id =  fields.Many2one('pappaya.fees.receipt','Receipt')
    is_select = fields.Boolean(string='Select')
    name =  fields.Char('Fee Receipt')
    enrollment_number = fields.Char('Enrollment Number')
    grade_id = fields.Many2one('pappaya.grade', 'Class', required=1)
    student_id = fields.Many2one('pappaya.student', 'Student')
    receipt_date = fields.Date('Receipt Date')
    payment_mode = fields.Selection([('cash','Cash'),('cheque/dd','Cheque'),('dd','DD'),('neft/rtgs','Neft/RTGS'),('card','POS')],string='Payment Mode')
    cheque_dd = fields.Char('Cheque/DD/POS/Ref. No')
    #total = fields.Float('Total')
    total = fields.Float(related='receipt_id.total', string='Total')
    state = fields.Selection([('draft','In hand'),('deposit','Deposited')],string='Status', default="draft")
    receipt_status = fields.Selection([('cleared','Cleared'),('uncleared','Uncleared')], string='Status', default='uncleared')
    attachment = fields.Binary(string="Attachment")
    
    file_name = fields.Char('Attachment')
    bank_clearance_id = fields.Many2one('bank.deposit.clearance', string='Bank Deposit Clearance')
    read_only = fields.Boolean(string="Read Only?")
    
    
class PaymentStatusLine(models.Model):
    _name = 'payment.status.line'

    receipt_id =  fields.Many2one('pappaya.fees.receipt','Receipt')
    is_select = fields.Boolean(string='Select')
    name =  fields.Char('Fee Receipt')
    enrollment_number = fields.Char('Enrollment Number')
    grade_id = fields.Many2one('pappaya.grade', 'Class', required=1)
    student_id = fields.Many2one('pappaya.student', 'Student')
    receipt_date = fields.Date('Receipt Date')
    payment_mode = fields.Selection([('cash','Cash'),('cheque/dd','Cheque'),('dd','DD'),('neft/rtgs','Neft/RTGS'),('card','POS')],string='Payment Mode')
    cheque_dd = fields.Char('Cheque/DD/POS/Ref. No')
    #total = fields.Float('Total')
    total = fields.Float(related='receipt_id.total', string='Total')
    #state = fields.Selection([('draft','Draft'),('deposit','Deposited')],string='Status', default="draft")
    state = fields.Selection([('cleared','Cleared'),('uncleared','Uncleared'),('rejected','Rejected')], string='Status', default='uncleared')
    attachment = fields.Binary(string="Attachment")
    file_name = fields.Char('Attachment')
    bank_clearance_id = fields.Many2one('bank.deposit.clearance', string='Bank Deposit Clearance')
    read_only = fields.Boolean(string="Read Only?")
    remarks = fields.Text(string='Remarks')
    clear_date = fields.Date('Clearance Date')
    
