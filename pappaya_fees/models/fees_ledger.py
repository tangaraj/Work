# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
from datetime import datetime




class PappayaFeesLedger(models.Model):
    _name = 'pappaya.fees.ledger'
    _rec_name = 'student_id'
      
      
    @api.model
    def _default_society(self):
        user_id = self.env['res.users'].sudo().browse(self.env.uid)
        if len(user_id.company_id.parent_id)>0 and user_id.company_id.parent_id.type == 'society':
            return user_id.company_id.parent_id.id
        elif user_id.company_id.type == 'society':
            return user_id.company_id.id

    @api.model
    def _default_school(self):
        user_id = self.env['res.users'].sudo().browse(self.env.uid)
        if user_id.company_id and user_id.company_id.type == 'school':
            return user_id.company_id.id
      
    society_id = fields.Many2one('res.company','Society', default=_default_society)
    school_id = fields.Many2one('res.company', 'School', default=_default_school)
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    enrollment_number = fields.Char('Enrollment Number')
    grade_id = fields.Many2one('pappaya.grade', 'Class', required=1)
    student_id = fields.Many2one('pappaya.student', 'Student')
    #~ fees_receipt_line =  fields.One2many('pappaya.fees.receipt.line','receipt_id','Receipt Line')
    fee_ledger_line = fields.One2many('pappaya.fees.ledger.line','fees_ledger_id','Ledger')
    fee_receipt_ledger_line = fields.One2many('pappaya.fees.receipt.ledger','fees_ledger_id', 'Ledger Receipt')
    
    fee_receipt_pos_line = fields.One2many('pappaya.fees.receipt.pos.ledger','fees_ledger_id', 'POS Transaction History')
    
    fee_collection_id = fields.Many2one('pappaya.fees.collection', 'Collection ID')
    active = fields.Boolean('Active', default=True)
    fee_refund_ledger_line = fields.One2many('pappaya.fees.refund.ledger','fees_ledger_id','Refund')
    fee_cancel_ledger_line = fields.One2many('pappaya.fees.cancel.ledger','fees_ledger_id','Cancel')
    
    
    @api.multi
    def get_school(self):
        school_list = []
        if self.school_id:
            vals = {}
            vals['school_id'] = self.school_id.name
            vals['logo'] = self.school_id.logo
            vals['street'] = self.school_id.street if self.school_id.street else ''
            vals['street2'] = self.school_id.street2 if self.school_id.street2 else ''
            vals['city'] = self.school_id.city if self.school_id.city else ''
            vals['zip'] = self.school_id.zip if self.school_id.zip else ''
            vals['phone'] = self.school_id.phone if self.school_id.phone else ''
            vals['fax'] = self.school_id.fax_id if self.school_id.fax_id else ''
            vals['email'] = self.school_id.email if self.school_id.email else ''
            vals['website'] = self.school_id.website if self.school_id.website else ''
            school_list.append(vals)
        return school_list 
    
    @api.multi
    def generate_ledger_report(self):
        for record in self:
            return self.env['report'].get_action(self, 'pappaya_fees.report_student_fee_ledger')
    
    @api.one
    def copy(self, default=None):
        raise ValidationError("You are not allowed to Duplicate")  
      
      
		
class PappayaFeesLedgerLine(models.Model):
    _name = 'pappaya.fees.ledger.line'


    name = fields.Char('Fees Head')
    credit = fields.Float('Total Fee')
    debit = fields.Float('Fee Deposited')
    balance = fields.Float('Fee Due')
    fees_ledger_id = fields.Many2one('pappaya.fees.ledger','Ledger')
    concession_type_id = fields.Many2one('pappaya.concession.type', 'Concession Type')
    concession_amount = fields.Float('Concession')
    refund_amount = fields.Float('Refund Amount')


class PappayaFeesReceiptLedger(models.Model):
    _name = 'pappaya.fees.receipt.ledger'
    
    name = fields.Char('Receipt No')
    posting_date = fields.Date('Transaction Date')
    fees_head = fields.Char('Fees Head')
    transaction = fields.Char('Remarks')
    amount = fields.Float('Amount')
    concession_amount = fields.Float('Concession')
    payment_mode = fields.Selection([('cash', 'Cash'),('cheque/dd','Cheque'),('dd','DD'), ('neft/rtgs', 'Neft/RTGS'), ('card', 'POS')], string='Payment Mode')
    fees_ledger_id = fields.Many2one('pappaya.fees.ledger','Ledger')
    fees_receipt_id = fields.Many2one('pappaya.fees.receipt','Receipt ID')

class PappayaFeesReceiptPosLedger(models.Model):
    _name = 'pappaya.fees.receipt.pos.ledger'
    
    
    date = fields.Date('Transaction Date')
    name = fields.Char('Receipt No')
    fees_head = fields.Char('Fees Head')
    actual_amount = fields.Float('Actual Amount')
    paid_amount = fields.Float('Paid Amount') 
    concession_amount = fields.Float('Concession')
    payment_mode = fields.Selection([('cash', 'Cash'), ('cheque/dd', 'Cheque/DD'), ('neft/rtgs', 'Neft/RTGS'), ('card', 'POS')], string='Payment Mode')
    fees_ledger_id = fields.Many2one('pappaya.fees.ledger','Ledger')
    fees_receipt_id = fields.Many2one('pappaya.fees.receipt','Receipt ID')
    pos_percentage = fields.Float('Pos %')
    pos_total = fields.Float('POS Amount')
    remarks = fields.Char('Remarks')
    

class pappayaFeesRefundLegder(models.Model):
    _name = 'pappaya.fees.refund.ledger'
       
       
    fees_head = fields.Char('Fees Head')
    amount = fields.Float('Amount')
    posting_date = fields.Date('Refund Date')
    fees_ledger_id = fields.Many2one('pappaya.fees.ledger','Ledger')
    
    
class pappayaFeesCancelLegder(models.Model):
    _name = 'pappaya.fees.cancel.ledger'
       
       
    fees_head = fields.Char('Fees Head')
    amount = fields.Float('Amount')
    posting_date = fields.Date('Cancel Date')
    fees_ledger_id = fields.Many2one('pappaya.fees.ledger','Ledger')
    
    
