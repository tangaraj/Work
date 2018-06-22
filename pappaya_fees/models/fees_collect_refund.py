# -*- coding: utf-8 -*-
import time
from openerp import models, fields, api, _
from openerp import workflow
from openerp.exceptions import ValidationError, UserError
from datetime import datetime


class FeesCollectRefund(models.Model):
    _name='fees.collect.refund'
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
    
    
    
    society_id = fields.Many2one('res.company', 'Society', default=_default_society)
    school_id = fields.Many2one('res.company', 'School', default=_default_school)
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    grade_id = fields.Many2one('pappaya.grade', 'Class')
    student_id = fields.Many2one('pappaya.student',string='Student')
    enrollment_number = fields.Char('Enrollment Number')
    remarks = fields.Text('Remarks')
    refund_fee_collection =fields.One2many('refund.fees.collection','collect_refund_id','Refund Collection Line')
    state = fields.Selection([('draft', 'Draft'), ('requested', 'Requested'),
                            ('approved', 'Approved'), ('rejected', 'Rejected'),('refund', 'Refunded')],
                            string='Status', readonly=True, default='draft')
    payment_mode = fields.Selection([('cash', 'Cash'), ('cheque/dd', 'Cheque'),('dd', 'DD'), ('neft/rtgs', 'NEFT/RTGS')], string='Payment Mode')
    cheque_dd = fields.Char('Cheque/DD/POS/Ref. No')
    bank_name = fields.Char('Bank name')
    total_refund_amount = fields.Float('Refund Amount', compute='calculate_refund_amount')
    collection_id = fields.Many2one('pappaya.fees.collection','Collection ID')
    
    @api.depends('total_refund_amount','refund_fee_collection')
    def calculate_refund_amount(self):
        for record in self:
            total_amount = 0.00
            for line in record.refund_fee_collection:
                if line.pay and line.refund_amount:
                    total_amount += line.refund_amount
            record.total_refund_amount = total_amount

    @api.one
    @api.constrains('refund_fee_collection')
    def refund_amount_checking(self):
        for record in self:
            for line in record.refund_fee_collection:
                if line.pay and line.refund_amount and line.amount < line.refund_amount and ((line.total_paid - line.concession_amount) - line.fee_refund_amount) < line.refund_amount :
                    raise ValidationError("Please pay actual amount")

    @api.onchange('society_id')
    def onchange_society_id(self):
        self.academic_year_id= None
        

#     @api.one
#     @api.constrains('student_id')
#     def _check_unique_name(self):
#         if self.student_id:
#             if len(self.search([('grade_id','=',self.grade_id.id),('school_id','=',self.school_id.id),('academic_year_id','=',self.academic_year_id.id),('student_id','=',self.student_id.id)]))>1:
#                 raise ValidationError("Fee refund for the selected student already exists")


    @api.multi
    @api.onchange('school_id')
    def get_academic_year(self):
        self.academic_year_id = None
        if self.school_id:
            self.academic_year_id = self.env['academic.year'].sudo().search(
            [('school_id', '=', self.school_id.id), ('is_active', '=', True)],limit=1)
                
    
    
    @api.onchange('student_id')
    def onchange_refund(self):
        self.enrollment_number =None
        if self.student_id:
            self.enrollment_number = self.student_id.enrollment_num 
            self.refund_fee_collection = None
            fee_collect = self.env['pappaya.fees.collection'].search([('active','=',True),('academic_year_id', '=', self.academic_year_id.id), ('grade_id', '=', self.grade_id.id),('school_id','=',self.school_id.id),('society_id','=',self.society_id.id),('student_id','=',self.student_id.id)])
            ids = []
            if fee_collect:
                for collect in fee_collect:
                    self.collection_id = collect.id
                    for line in collect.fees_collection_line:
                        if line.total_paid > 0.00:
                            ids.append({
                                        'name':line.name,
                                        'concession_type_id':line.concession_type_id.id,
                                        'term_divide':line.term_divide,
                                        'amount':line.amount,
                                        'concession_amount':line.concession_amount,
                                        'concession_applied':line.concession_applied,
                                        'partial_payment':line.partial_payment,
                                        'due_amount':line.due_amount,
                                        'total_paid':line.total_paid,
                                        'term_state':line.term_state,
                                        'collect_refund_id': self.id,
                                        'readonly_state':'draft',
                                        'fee_refund_amount':line.refund_amount 
                                    })
                        else:
                            ids.append({
                                        'name':line.name,
                                        'concession_type_id':line.concession_type_id.id,
                                        'term_divide':line.term_divide,
                                        'amount':line.amount,
                                        'concession_amount':line.concession_amount,
                                        'concession_applied':line.concession_applied,
                                        'partial_payment':line.partial_payment,
                                        'due_amount':line.due_amount,
                                        'total_paid':line.total_paid,
                                        'term_state':line.term_state,
                                        'collect_refund_id': self.id,
                                        'readonly_state':'done',
                                        'fee_refund_amount':line.refund_amount 
                                    })
            self.update({'refund_fee_collection':ids})
            print self.collection_id,"211111111111111111111"
#          return True
            
            
    
    
    
    
    @api.model
    def create(self, vals):
        if 'student_id' in vals:
            enq = self.env['pappaya.student'].browse(vals['student_id'])
            vals['enrollment_number'] = enq.enrollment_num
        res = super(FeesCollectRefund, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        if 'student_id' in vals:
            enq = self.env['pappaya.student'].browse(vals['student_id'])
            vals['enrollment_number'] = enq.enrollment_num
        res = super(FeesCollectRefund, self).write(vals)
        return res
    
    @api.multi
    def request_in_refund(self):
        self.sudo().write({'state': 'requested'})
    
    
    @api.multi
    def act_approve_refund(self):
        self.sudo().write({'state': 'approved'})

    
    @api.multi
    def act_reject_refund(self):
        self.sudo().write({'state': 'rejected'})

    @api.multi
    def confirm_refund(self):
        #fee_collect = self.env['pappaya.fees.collection'].search([('active','=',True),('grade_id', '=', self.grade_id.id), ('student_id', '=', self.student_id.id),('school_id', '=', self.school_id.id),('society_id', '=', self.society_id.id),('academic_year_id', '=', self.academic_year_id.id)])
        ledger_obj= self.env['pappaya.fees.ledger'].search([('fee_collection_id','=',self.collection_id.id)])
        refund_obj = self.env['pappaya.fees.refund']
        receipt_obj = self.env['pappaya.fees.receipt'].search([('fee_collection_id','=',self.collection_id.id)])
        print self.collection_id,"22222222222222222222222222" 
        
        fee_ledger_line = []
        fees_refund_line = []
        for record in self:
            for refund_line in record.refund_fee_collection:
                for collection_line in record.collection_id.fees_collection_line:
                    if refund_line.name in collection_line.name and refund_line.pay and refund_line.refund_amount:

                        collection_line.sudo().write({'refund_amount':collection_line.refund_amount + refund_line.refund_amount,
                                                      'due_amount':collection_line.due_amount + refund_line.refund_amount,
                                                      'total_paid': collection_line.total_paid - refund_line.refund_amount
                                                      })
                        if collection_line.due_amount:
                            collection_line.sudo().write({'term_state':'due'}) 
                        fees_refund_line.append((0, 0, {
                                                'name':refund_line.name,
                                                'term_divide':refund_line.term_divide,
                                                'amount':refund_line.refund_amount
                                                }))
                if refund_line.pay and refund_line.refund_amount:
                    refund_line.sudo().write({'term_state':'fee_refund'})

        
        
            for rec1 in record.collection_id.fees_collection_line:
                fee_ledger_line.append((0, 0, {
                                                'name':rec1.name,
                                                'credit':rec1.amount,
                                                'concession_amount':rec1.concession_amount,
                                                'concession_type_id':rec1.concession_type_id.id,
                                                'refund_amount':rec1.refund_amount,
                                                'debit':rec1.total_paid,
                                                'balance':(rec1.amount) - (rec1.total_paid + rec1.concession_amount+rec1.refund_amount),
                                                }))
            
        
        refund_receipt = refund_obj.sudo().create({
                'society_id': self.society_id.id,
                'school_id' : self.school_id.id,
                'academic_year_id' : self.academic_year_id.id,
                'enrollment_number' : self.enrollment_number,
                'payment_mode':self.payment_mode,
                'cheque_dd':self.cheque_dd,
                'bank_name':self.bank_name,
                'remarks':self.remarks,
                'grade_id' : self.grade_id.id,
                'student_id' : self.student_id.id,
                'refund_date':datetime.today().date(),
                'fee_refund_line':fees_refund_line
                        
                })
        if refund_receipt:
            fee_refund_ledger_line = []
            for frl in refund_receipt.fee_refund_line:
                fee_refund_ledger_line.append((0, 0, 
                                            {
                        'posting_date':refund_receipt.refund_date,
                        'fees_head':frl.name,
                        'amount':frl.amount,
                                                }
                                            ))
        for ledger in ledger_obj:
            #ledger.fee_refund_ledger_line.sudo().unlink()
            ledger.fee_refund_ledger_line = fee_refund_ledger_line
            ledger.fee_ledger_line.sudo().unlink()
            #lbr.fee_receipt_ledger_line = fee_receipt_ledger_line
            ledger.fee_ledger_line = fee_ledger_line
        #self.collection_id.sudo().write({'bulk_term_state': 'fee_refund'}) 
        #receipt_obj.sudo().write({'state':'refund'})
        self.sudo().write({'state': 'refund'})

class RefundFeeCollection(models.Model):
    _name='refund.fees.collection'

    pay = fields.Boolean('Pay')
    name = fields.Char('Fees Head')
    concession_type_id = fields.Many2one('pappaya.concession.type', 'Concession Type')
    term_divide = fields.Selection([('1', 'Term-1'), ('2', 'Term-2'), ('3', 'Term-3'), ('4', 'Term-4'), ('5', 'Term-5'), ('6', 'Term-6'), ('7', 'Term-7'), ('8', 'Term-8'), ('9', 'Term-9'), ('10', 'Term-10')], string='Term No')
    partial_payment = fields.Boolean('Partial Payment')
    amount = fields.Float('Amount')
    concession_amount = fields.Float('Concession')
    concession_applied = fields.Boolean('Concession Applied')
    due_amount = fields.Float('Due Amount')
    fee_refund_amount = fields.Float('Fee Refund Amount')
    refund_amount = fields.Float('Refund Amount')
    total_paid = fields.Float('Total Paid')
    term_state = fields.Selection([('due', 'Due'), ('paid', 'Paid'), ('refund', 'Transferred'),('fee_refund','Refund')], 'Status')
    collect_refund_id = fields.Many2one('fees.collect.refund','Refund Collect')
    readonly_state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], 'Status')







