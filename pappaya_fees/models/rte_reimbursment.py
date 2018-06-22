# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
from datetime import datetime
import re
import os
import time

class PappayaRteReimbursment(models.Model):
    _name = 'pappaya.rte.reimbursment'
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

    @api.model
    def _default_start(self):
        return fields.Date.context_today(self)


    society_id = fields.Many2one('res.company', 'Society', default=_default_society)
    school_id = fields.Many2one('res.company', 'School', default=_default_school)
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    date = fields.Date(string="Date", default=_default_start, readonly=True)
    total_amt = fields.Float(string="Total Amount", compute='total_rte_calculate_fees', store=True)
    total_cal = fields.Float(string="Total Amount", compute='total_rte_calculate_fees', store=True)
    paid_amt = fields.Float(string="Amount Received From (Govt.)")
    pending_amt = fields.Float(string="Pending Amount", compute='rte_fees', store=True)
    rte_fee_reimbursment = fields.One2many('rte.fee.reimbursment.line', 'ret_fee_id', string="Rte Fee Reimbursment")
    rte_pay = fields.Boolean()
    
    payment_mode = fields.Selection([('cash', 'Cash'), ('cheque', 'Cheque'),('dd', 'DD'), ('neft/rtgs', 'NEFT/RTGS')], string='Payment Mode')
    #file = fields.Binary(string="RTE Receipt Upload")
    #filename = fields.Char('File name', readonly = True,store = False, compute ='doc1_getFilename')
    
    rte_receipt_attachments = fields.Many2many('ir.attachment', string="Attachments")
    cheque_dd = fields.Char('Cheque/DD/POS/Ref. No')
    bank_name = fields.Char('Bank name')
    remarks = fields.Text('Remarks')
    pay_fees = fields.Boolean(string="Record Amount")
    rte_received_line_ids = fields.One2many('rte.received.amount', 'received_id')
    rte_refund_fees = fields.Boolean()
    rte_students_list = fields.Many2many('pappaya.student')
    view_student = fields.Boolean(string="To view Students, click here")
    
    
    @api.one
    @api.constrains('academic_year_id')
    def avoid_duplicate(self):
        if not self.rte_fee_reimbursment.ids:
            raise ValidationError(("No RTE Students available, please click on Discard"))
    
    @api.one    
    @api.onchange('rte_receipt_attachments')
    def doc1_getFilename(self):
        today = time.strftime('_%d_%b_%Y_')
        count = 1
        for attachment in self.rte_receipt_attachments:
            name, ext = os.path.splitext(attachment.name)
            attachment.write({'name':'RTE_receipt_' + str(self.payment_mode) + str(today) + (str(count)) +  ext,'datas_fname':'RTE_receipt_' + str(self.payment_mode) + str(today) + (str(count)) +  ext})
            count += 1
             
            
        
        
    @api.onchange('academic_year_id')
    def calculate_rte_fees(self):
        if self.academic_year_id:
            grade_records = self.env['pappaya.grade'].search([])
            rte_fee_reimbursment_list = []
            lst = []
            exist_students= []
            rte_exist_student = self.search([('society_id', '=', self.society_id.id),
                                            ('school_id', '=', self.school_id.id),
                                            ('academic_year_id', '=', self.academic_year_id.id)])
            
            for re in rte_exist_student: 
                for student in re.rte_students_list:
                    exist_students.append(student.id)
            
            for grade in grade_records:
                rte_records = self.env['pappaya.student'].search([
                                        ('id', 'not in', exist_students),
                                        ('society_id', '=', self.society_id.id),
                                        ('school_id', '=', self.school_id.id),
                                        ('academic_year_id', '=', self.academic_year_id.id),
                                        ('enquiry_mode', '=', 'rte'), ('grade_id', '=', grade.id)])
                
                
                if rte_records:
                    
                    for rec in rte_records:
                        lst.append(rec.id)
                    
                    no_of_student = len(rte_records)
                    rte_fee_reimbursment_list.append({
                                                       'no_of_rte':no_of_student,
                                                       'grade_id':grade.id,
                                                       'actual_fee':0.0,
                                                       'book_fee':0.0,
                                                       'dress_fees':0.0,
                                                       'total_fees_student':0.0,
                                                       'total_amt':0.0})
                    
                    self.rte_fee_reimbursment = rte_fee_reimbursment_list
                self.rte_students_list = lst
                    
                    
                    
                    
                    
    
    @api.multi
    @api.depends('rte_fee_reimbursment')
    def total_rte_calculate_fees(self):
        if not self.rte_pay:
            amount = 0
            for line in self.rte_fee_reimbursment:
                for g in line:
                    amount += line.total_amt
                self.total_amt = amount
                self.total_cal = amount
#             self.pending_amt = amount     
                        
    
    @api.depends('total_cal')
    def rte_fees(self):
        self.pending_amt = self.total_amt
       
       
    @api.multi
    def fee_rte_process(self):
        if self.pay_fees and self.paid_amt == 0:
            raise ValidationError(("Please check the amount"))
        if self.pay_fees and self.pending_amt == 0.0:
            raise ValidationError(("Please check the pending amount"))
        if self.total_amt == self.pending_amt:
            b = self.total_amt - self.paid_amt
            self.pending_amt = b
        else:
            b = self.pending_amt - self.paid_amt
            self.pending_amt = b
        
        rte_list = []
        file_attach = []
        for attach in self.rte_receipt_attachments:
            file_attach.append((0,0, {
                                        'datas': attach.datas,
                                        'datas_fname':attach.datas_fname,
                                        'name':attach.name,
                                        'res_model':'rte.received.amount'
                                    }))
        if self.paid_amt:
            rte_list.append((0, 0, {'received_amt': self.paid_amt,
                                    'received_date':datetime.today().date(),
                                    'received_id':self.id,
                                    'payment_mo':self.payment_mode,
                                    'rte_receipt_attachments':file_attach,
                                    'remarks':self.remarks
                                    })) 
            self.write({'rte_received_line_ids':rte_list})
        self.paid_amt = 0.0
        self.rte_pay = True
        self.payment_mode = False
        self.rte_receipt_attachments = False
        self.pay_fees = False
        self.cheque_dd = False
        self.bank_name = False
        self.remarks = False

    @api.one
    @api.constrains('paid_amt')
    def check_paid_amt(self):
        if self.paid_amt > self.pending_amt:
            raise ValidationError(("Please check, Paid Amount is not greater than Pending Amount"))

        
    @api.constrains('paid_amt')
    def _check_negative_amount(self):
        mark_matchs = re.match('^[0.-9.]+$', str(self.paid_amt))
        if not mark_matchs:
            raise ValidationError(_("Please enter proper amount.!"))
        
#     @api.one
#     @api.constrains('society_id', 'school_id', 'academic_year_id')
#     def _check_unique_name(self):
#         if self.society_id and self.school_id and self.academic_year_id:
#             if len(self.search([('society_id', '=', self.society_id.id), ('school_id', '=', self.school_id.id),('academic_year_id', '=', self.academic_year_id.id)])) > 1:
#                 raise ValidationError("Record already exists")
            
class rte_fee_reimbursment_line(models.Model):
    _name = 'rte.fee.reimbursment.line'
    
    @api.one
    @api.depends('actual_fee', 'book_fee', 'dress_fees')
    def rte_calculate_fees(self):
        for rec in self:
            if rec.ret_fee_id.rte_fee_reimbursment:
                for fee in rec.ret_fee_id.rte_fee_reimbursment:
                    for g in fee:
                        g.total_fees_student = g.actual_fee + g.book_fee + g.dress_fees
                        g.total_amt = g.total_fees_student * g.no_of_rte
                    

    rte_student_id = fields.Many2one('pappaya.student', string="RTE Student")
    no_of_rte = fields.Integer(string="No.of Students")
    grade_id = fields.Many2one('pappaya.grade', string="Class")
    actual_fee = fields.Float(string="Actual Fees Per Student",)
    book_fee = fields.Float(string="Book Fees Per Student")
    dress_fees = fields.Float(string="Dress Fees Per Student")
    total_fees_student = fields.Float(string="Total Fees Per Student", compute='rte_calculate_fees')
    total_amt = fields.Float(string="Total Fees Amount", compute='rte_calculate_fees')
    ret_fee_id = fields.Many2one('pappaya.rte.reimbursment')
    rte_students_ids = fields.Many2one('pappaya.student')
    
    
    @api.constrains('actual_fee', 'book_fee', 'dress_fees')
    def _check_negative_amount(self):
        actual_fee = re.match('^[0.-9.]+$', str(self.actual_fee))
        if not actual_fee:
            raise ValidationError(_("Please enter proper amount.!"))
        book_fee = re.match('^[0.-9.]+$', str(self.book_fee))
        if not book_fee:
            raise ValidationError(_("Please enter proper amount.!"))
        dress_fees = re.match('^[0.-9.]+$', str(self.dress_fees))
        if not dress_fees:
            raise ValidationError(_("Please enter proper amount.!"))
    
    
class RteReceivedAmount(models.Model):
    _name = 'rte.received.amount'
    
    received_amt = fields.Float(string="Received Amount")
    received_date = fields.Date(string="Received Date")
    received_id = fields.Many2one('pappaya.rte.reimbursment')
#     payment_mo = fields.Char(string="Payment Mode")
    payment_mo = fields.Selection([('cash', 'Cash'),('cheque','Cheque'),('dd','DD'), ('neft/rtgs', 'NEFT/RTGS')], string='Payment Mode')
    rte_receipt_attachments = fields.Many2many('ir.attachment', string="Attachments")
    remarks = fields.Char()
