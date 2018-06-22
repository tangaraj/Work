# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
from datetime import datetime

class Pappaya_fees_collection(models.Model):
    _name = 'pappaya.fees.collection'
    _rec_name = 'grade_id'
    _order = "enrollment_number desc"
    
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
    enrollment_number = fields.Char('Enrollment Number')
    grade_id = fields.Many2one('pappaya.grade', 'Class', required=1)
    student_id = fields.Many2one('pappaya.student', 'Student Name')
    applicant_name = fields.Char('Student Name')
    fees_collection_line = fields.One2many('student.fees.collection', 'collection_id', 'Collection Line')
    #~ fees_bulk_line = fields.One2many('student.fees.bulk.line', 'collection_id', 'Bulk Payment')
    bulk_pay = fields.Boolean('Bulk Payment')
    enquiry_create = fields.Boolean('Enquiry')
    pay_amount = fields.Float('Pay Amount')
    total = fields.Float('Grand Total', compute='compute_total')
    enquiry_mode = fields.Selection([('normal', 'Normal'), ('rte', 'RTE')], default='normal')
    rte_fee_exempted = fields.Boolean('Full Waiver Under RTE?')
    # ~ bulk_state = fields.Selection([('due', 'Due'), ('paid', 'Paid')],'Status',default='due')
    bulk_term_state = fields.Selection([('due', 'Due'), ('paid', 'Paid'), ('refund', 'Transferred'),('fee_refund','Refund')], 'Status', default='due', compute='compute_state_term')
    payment_mode = fields.Selection([('cash', 'Cash'), ('cheque/dd', 'Cheque'),('dd', 'DD'), ('neft/rtgs', 'NEFT/RTGS'),('card','POS')], string='Payment Mode')
    cheque_dd = fields.Char('Cheque/DD/POS/Ref. No')
    bank_name = fields.Char('Bank name')
    remarks = fields.Text('Remarks')
    due_total = fields.Float('Total due', compute='compute_total_due')
    paid_total = fields.Float('Total paid', compute='compute_total_paid')
    active = fields.Boolean('Active', default=True)
    excess_amt=fields.Char(string="Excess Amount")
    collection_date = fields.Date(string="Collection Date",)
    
    pay_due_total = fields.Float('Pay due',compute='compute_pay_due')
    pos_total = fields.Float('PoS Amount')
    pos_percentage = fields.Float('PoS %')
    #file = fields.Many2many("ir.attachment",string='File Upload', type="Binary", required=True, help='File Upload attachment')
    current_user = fields.Many2one('res.users','Current User', default=lambda self: self.env.user)
    # ~ due_bulk = fields.Float('Due amount')
    # ~ total_bulk = fields.Float('Grand Total',compute ='compute_total_bulk')
    
    @api.one
    @api.depends('fees_collection_line','pay_due_total')
    def compute_pay_due(self):
        amt = 0.0
        for line in self.fees_collection_line:
            if line.pay and line.term_state == 'due':
                amt +=  line.due_amount
        self.pay_due_total += amt    
            
    @api.one
    @api.depends('fees_collection_line','pay_amount','pos_percentage','pos_total')
    def compute_pos_total(self):
        if self.pay_amount and self.pos_percentage:
            pos_discount = self.pay_amount * self.pos_percentage/100
            self.pos_total = self.pay_amount - pos_discount
    
    
    @api.multi 
    @api.constrains('collection_date')
    def collection_date_validation(self):
        for r in self:
            if r.academic_year_id.start_date:
                if r.collection_date and r.collection_date >= r.academic_year_id.start_date and r.collection_date > str(datetime.today().date()):
                    raise ValidationError("Collection should not be in future date.!")
                
    
    @api.multi
    @api.depends('payment_mode')
    def compute_pos_percentage(self):

        if self.payment_mode == 'cash':
            self.cheque_dd = None
            self.bank_name = None
            
        if self.payment_mode == 'card':
            pos_structure_sr = self.env['pappaya.pos.structure'].search([('academic_year_id', '=', self.academic_year_id.id), ('society_ids', 'in', self.society_id.id),('school_ids','in',self.school_id.id)])
            if pos_structure_sr:
                self.pos_percentage = pos_structure_sr[0].pos_percentage

        
    @api.multi
    @api.depends('fees_collection_line.amount')
    def compute_total(self):
        for rec in self:
            rec.total = round(sum(line.amount for line in rec.fees_collection_line))
    
    

    
    @api.multi
    @api.depends('fees_collection_line.total_paid')     
    def compute_total_paid(self):
        for rec in self:
            rec.paid_total = round(sum(line.total_paid for line in rec.fees_collection_line))
    
    @api.multi
    @api.depends('fees_collection_line.due_amount')
    def compute_total_due(self):
        for rec in self:
            rec.due_total = round(sum(line.due_amount for line in rec.fees_collection_line))
    
    @api.depends('due_total')
    def compute_state_term(self):
        for rec in self:
    	    if rec.due_total:
    	       rec.bulk_term_state = 'due'
    	    if rec.due_total == 0.0:
    	       rec.bulk_term_state = 'paid'
    	    for i in rec.fees_collection_line:
                if i.term_state == 'refund':
                    rec.bulk_term_state = 'refund'
                if i.term_state == 'fee_refund':
                    rec.bulk_term_state = 'fee_refund'
        		    
    
    @api.constrains('pay_amount')
    def _check_pay_amount(self):
        if self.pay_amount < 0.0:
            raise ValidationError(_("The value of amount should be positive !"))

    @api.onchange('grade_id')
    def onchange_grade(self):
        fee_head = self.env['pappaya.fees.structure'].search([('academic_year_id', '=', self.academic_year_id.id), ('grade_ids_m2m', 'in', self.grade_id.id),('school_ids','in',self.school_id.id)])    
        ids = []
        if fee_head:
            for i in fee_head:
                for head in i.fee_term_line:
                    ids.append({
                            'name':head.name,
                            'term_divide':head.term_divide,
                            'amount':head.amount,
                            'partial_payment':head.partial_payment,
                            'collection_id': self.id,
                            'term_state':'due',  # self.fees_collection_line.term_state,
                        })
            self.update({'fees_collection_line':ids})
        return True

    @api.multi
    def fee_pay(self):
        
        uid = 1
        pay_due_total = pos_percentage = pos_total = 0.0
        pay_due_total = self.pay_due_total
        pos_percentage = self.pos_percentage,
        pos_total = self.pos_total
        receipt_obj = self.env['pappaya.fees.receipt']
        ledger_obj = self.env['pappaya.fees.ledger']
        if self.pay_amount == 0.0:
            raise ValidationError("Pay actual amount")
        for record in self.sudo():
#             count = 0
#             for rec in record.fees_collection_line: 
#                 if rec.pay:
#                     count += 1
#             if count > 1:
#                 raise ValidationError("Please select only one fees at a time")
            #fee_ledger_line = []
            fees_receipt_line_list = []
            remaing_amount = record.pay_amount
            if record.pay_amount:
                enquiry_mode_code = ''
                if record.enquiry_id.enquiry_mode == 'normal':
                    enquiry_mode_code = 'N'
                if record.enquiry_id.enquiry_mode == 'rte':
                    enquiry_mode_code = 'R'
        
                #~ state_code = self.school_id.parent_id.code
                school_code = record.enquiry_id.school_id.code
        
                academic_year = record.academic_year_id.start_date[:4]
                stu_enr_se_no = record.enquiry_id.sname
                
                order_line_ids=[]
                for rec_line in record.fees_collection_line:
                    if not rec_line.pay and rec_line.term_state == 'due':
                        order_line_ids.append(rec_line.name)
                    if rec_line.pay and rec_line.term_state == 'due':
                        if order_line_ids:
                            raise ValidationError("Please pay Fees in order to proceed")
                        else:
                            break
                            
                    
                for rec in record.fees_collection_line:
                    if 'Reg' in rec.name and rec.amount > 0.00:
                        if rec.term_state == 'due' and rec.pay:
                            if rec.due_amount <= remaing_amount:
                                rec.total_paid += rec.due_amount
                                remaing_amount -= rec.total_paid
                                if rec.amount == rec.total_paid:
                                    rec.term_state = 'paid'
                                    if rec.due_amount > 0.00:
                                        fees_receipt_line_list.append((0, 0, {
                                                                'name':rec.name,
                                                                'term_divide':rec.term_divide,
                                                                'amount':rec.due_amount,
                                                               'concession_amount':rec.concession_amount
                                                                 
                                                     }))
                                    if not record.enquiry_id.state == 'reg_process':
                                        record.sudo().enquiry_id.state = 'reg_process'
                                    if not record.student_id:
                                        valss = record.sudo().enquiry_id.get_student_vals()
                                        stud_id = self.env['pappaya.student'].sudo().create(valss)
                                        self.sudo().write({'student_id': stud_id.id})
                                        self.sudo().write({'enquiry_create':True})
                                        record.sudo().enquiry_id.stud_id = stud_id.id
                                        record.sudo().enquiry_id.enrollment_number = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        self.enrollment_number =  str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        enroll = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        stud_id.sudo().write({'siblings_ids': [(6,0, list(stud_id.enquiry_id.siblings_line.ids))],'enrollment_num':enroll})
                                        for sib in stud_id.enquiry_id.siblings_line:
                                            enrollment_num = sib.enq_enroll
                                            if enrollment_num:
                                                student_record = self.env['pappaya.student'].search([('enrollment_num', '=', enrollment_num)])
                                                if student_record:
                                                    student_record.sudo().write({'siblings_ids': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})

                                                else:
                                                    enquiry_details = self.env['pappaya.enquiry'].search([('name', '=', enrollment_num)])
                                                    if enquiry_details:
                                                        enquiry_details.sudo().write({'siblings_line': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})

                            else:
                                raise ValidationError("Please pay registration fees actual amount")
                                    
                        elif rec.term_state == 'due' and not rec.pay:
                            raise ValidationError("Please pay Registration Fees in order to proceed")
                    
                    if 'Adm' in rec.name and rec.amount > 0.00:
                        if rec.term_state == 'due' and rec.pay:
                            if not rec.partial_payment:
                                rec.due_amount = rec.amount - rec.concession_amount - rec.total_paid
                                if rec.due_amount <= remaing_amount:
                                    receipt_amount = 0.00
                                    receipt_amount = rec.due_amount
                                    rec.total_paid = rec.due_amount
                                    
                                    remaing_amount -= rec.total_paid
                                    if rec.amount == (rec.total_paid + rec.concession_amount) or rec.due_amount == 0.00:
                                        rec.term_state = 'paid'
                                        if receipt_amount > 0.00:
                                            fees_receipt_line_list.append((0, 0, {
                                                                'name':rec.name,
                                                                'term_divide':rec.term_divide,
                                                                'amount':rec.due_amount,
                                                               'concession_amount':rec.concession_amount
                                                                 
                                                     }))
                                        if not record.enquiry_id.state == 'admitted':
                                            record.enquiry_id.stud_id.sudo().write({'state':'admitted'})
                                            record.sudo().enquiry_id.state = 'admitted'
                                            print "StudentSSSSSSSSSSSSSS",record.enquiry_id.stud_id.state
                                        if not record.student_id:
                                            valss = record.sudo().enquiry_id.get_student_vals()
                                            stud_id = self.env['pappaya.student'].sudo().create(valss)
                                            self.sudo().write({'student_id': stud_id.id})
                                            self.student_id.sudo().write({'state':'admitted'})
                                            record.sudo().enquiry_id.stud_id = stud_id.id
                                            record.sudo().enquiry_id.enrollment_number = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                            self.enrollment_number =  str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                            enroll = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                            stud_id.sudo().write({'siblings_ids': [(6,0, list(stud_id.enquiry_id.siblings_line.ids))],'enrollment_num':enroll})
                                            for sib in stud_id.enquiry_id.siblings_line:
                                                enrollment_num = sib.enq_enroll
                                                if enrollment_num:
                                                    student_record = self.env['pappaya.student'].search([('enrollment_num', '=', enrollment_num)])
                                                    if student_record:
                                                        student_record.sudo().write({'siblings_ids': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})
    
                                                    else:
                                                        enquiry_details = self.env['pappaya.enquiry'].search([('name', '=', enrollment_num)])
                                                        if enquiry_details:
                                                            enquiry_details.sudo().write({'siblings_line': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})
    
                                            
                                            
                                            
                                else:
                                    raise ValidationError('Please pay actual amount')        
                            else:
                                rec.due_amount = rec.amount - rec.concession_amount - rec.total_paid
                                if rec.due_amount <= remaing_amount:
                                    receipt_amount = 0.00
                                    receipt_amount = rec.due_amount
                                    rec.total_paid += rec.due_amount
                                    remaing_amount -= rec.due_amount
                                    if rec.amount == (rec.total_paid + rec.concession_amount) or rec.due_amount == 0.00:
                                        rec.term_state = 'paid'
                                        if receipt_amount > 0.00:
                                            fees_receipt_line_list.append((0, 0, {
                                                                'name':rec.name,
                                                                'term_divide':rec.term_divide,
                                                                'amount':rec.due_amount,
                                                               'concession_amount':rec.concession_amount
                                                                 
                                                     }))
                                    if not record.enquiry_id.state == 'admitted':
                                        record.enquiry_id.stud_id.sudo().write({'state':'admitted'})
                                        print "StudentSSSSSSSSSSSSSS",record.enquiry_id.stud_id.state
                                        record.sudo().enquiry_id.state = 'admitted'
                                        
                                    if not record.student_id:
                                        valss = record.enquiry_id.get_student_vals()
                                        stud_id = self.env['pappaya.student'].sudo().create(valss)
                                        self.write({'student_id': stud_id.id})
                                        self.student_id.write({'state':'admitted'})
                                        record.sudo().enquiry_id.stud_id = stud_id.id
                                        record.sudo().enquiry_id.enrollment_number = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        self.enrollment_number =  str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        enroll = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        stud_id.sudo().write({'siblings_ids': [(6,0, list(stud_id.enquiry_id.siblings_line.ids))],'enrollment_num':enroll})
                                        for sib in stud_id.enquiry_id.siblings_line:
                                            enrollment_num = sib.enq_enroll
                                            if enrollment_num:
                                                student_record = self.env['pappaya.student'].search([('enrollment_num', '=', enrollment_num)])
                                                if student_record:
                                                    student_record.sudo().write({'siblings_ids': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})

                                                else:
                                                    enquiry_details = self.env['pappaya.enquiry'].search([('name', '=', enrollment_num)])
                                                    if enquiry_details:
                                                        enquiry_details.sudo().write({'siblings_line': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})
                                
                                else:
                                    rec.total_paid += remaing_amount
                                    amt = 0.00
                                    amt = remaing_amount
                                    remaing_amount -= remaing_amount
                                    if amt > 0.00:
                                        fees_receipt_line_list.append((0, 0, {
                                                                'name':rec.name,
                                                                'term_divide':rec.term_divide,
                                                                'amount':amt,
                                                               'concession_amount':rec.concession_amount
                                                             
                                                 }))
                                    if rec.amount == (rec.total_paid + rec.concession_amount) or rec.due_amount == 0.00:
                                        rec.term_state = 'paid'
                                    self.student_id.sudo().write({'state':'admitted'})    
                                    if not record.enquiry_id.state == 'admitted':
                                        record.sudo().enquiry_id.state = 'admitted'
                                        print "StudentSSSSSSSSSSSSSS",record.enquiry_id.stud_id.state
                                        record.enquiry_id.stud_id.sudo().write({'state':'admitted'})
                                    if not record.student_id:
                                        valss = record.enquiry_id.get_student_vals()
                                        stud_id = self.env['pappaya.student'].sudo().create(valss)
                                        self.write({'student_id': stud_id.id})
                                        self.student_id.write({'state':'admitted'})
                                        record.sudo().enquiry_id.stud_id = stud_id.id
                                        record.sudo().enquiry_id.enrollment_number = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        self.enrollment_number =  str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        enroll = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        stud_id.sudo().write({'siblings_ids': [(6,0, list(stud_id.enquiry_id.siblings_line.ids))],'enrollment_num':enroll})
                                        for sib in stud_id.enquiry_id.siblings_line:
                                            enrollment_num = sib.enq_enroll
                                            if enrollment_num:
                                                student_record = self.env['pappaya.student'].search([('enrollment_num', '=', enrollment_num)])
                                                if student_record:
                                                    student_record.sudo().write({'siblings_ids': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})

                                                else:
                                                    enquiry_details = self.env['pappaya.enquiry'].search([('name', '=', enrollment_num)])
                                                    if enquiry_details:
                                                        enquiry_details.sudo().write({'siblings_line': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})
                            #if self.student_id.state != 'admitted':
                            record.enquiry_id.stud_id.sudo().write({'state':'admitted'})           
                                            
                    if  rec.term_divide and rec.amount > 0.00:
                        if rec.term_state == 'due' and rec.pay:
                            if not rec.partial_payment:
                                rec.due_amount = rec.amount - rec.concession_amount - rec.total_paid
                                if rec.due_amount <= remaing_amount:
                                    receipt_amount = 0.00
                                    receipt_amount = rec.due_amount
                                    rec.total_paid = rec.due_amount
                                    remaing_amount -= rec.total_paid
                                    if rec.amount == (rec.total_paid + rec.concession_amount) or rec.due_amount == 0.00:
                                        rec.term_state = 'paid'
                                        if receipt_amount > 0.00:
                                            fees_receipt_line_list.append((0, 0, {
                                                                'name':rec.name,
                                                                'term_divide':rec.term_divide,
                                                                'amount':rec.due_amount,
                                                               'concession_amount':rec.concession_amount
                                                                 
                                                     }))
                                        if not record.enquiry_id.state == 'done':
                                            record.sudo().student_id.write({'state':'done'})
                                            record.sudo().enquiry_id.state = 'done'
                                            
                                            
                                        if not record.student_id:
                                            valss = record.enquiry_id.get_student_vals()
                                            stud_id = self.env['pappaya.student'].sudo().create(valss)
                                            self.sudo().write({'student_id': stud_id.id})
                                            record.sudo().enquiry_id.stud_id = stud_id.id
                                            record.sudo().enquiry_id.enrollment_number = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                            self.enrollment_number =  str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                            enroll = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                            stud_id.sudo().write({'siblings_ids': [(6,0, list(stud_id.enquiry_id.siblings_line.ids))],'enrollment_num':enroll})
                                            for sib in stud_id.enquiry_id.siblings_line:
                                                enrollment_num = sib.enq_enroll
                                                if enrollment_num:
                                                    student_record = self.env['pappaya.student'].search([('enrollment_num', '=', enrollment_num)])
                                                    if student_record:
                                                        student_record.sudo().write({'siblings_ids': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})
    
                                                    else:
                                                        enquiry_details = self.env['pappaya.enquiry'].search([('name', '=', enrollment_num)])
                                                        if enquiry_details:
                                                            enquiry_details.sudo().write({'siblings_line': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})

                                else:
                                    raise ValidationError('Please pay actual amount')        
                            else:
                                rec.due_amount = rec.amount - rec.concession_amount - rec.total_paid
                                if rec.due_amount <= remaing_amount:
                                    
                                    receipt_amount = 0.00
                                    receipt_amount = rec.due_amount
                                    
                                    rec.total_paid += rec.due_amount
                                    remaing_amount -= rec.due_amount
                                    if rec.amount == (rec.total_paid + rec.concession_amount) or rec.due_amount == 0.00:
                                        rec.term_state = 'paid'
                                        if receipt_amount > 0.00:
                                            fees_receipt_line_list.append((0, 0, {
                                                                'name':rec.name,
                                                                'term_divide':rec.term_divide,
                                                                'amount':rec.due_amount,
                                                                'concession_amount':rec.concession_amount
                                                                 
                                                     }))
                                    if not record.enquiry_id.state == 'done':
                                        record.sudo().enquiry_id.state = 'done'
                                        record.enquiry_id.stud_id.sudo().write({'state':'done'})
                                        
                                    if not record.student_id:
                                        valss = record.enquiry_id.get_student_vals()
                                        stud_id = self.env['pappaya.student'].sudo().create(valss)
                                        self.sudo().write({'student_id': stud_id.id})
                                        record.sudo().enquiry_id.stud_id = stud_id.id
                                        record.sudo().enquiry_id.enrollment_number = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        self.enrollment_number =  str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        enroll = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        stud_id.sudo().write({'siblings_ids': [(6,0, list(stud_id.enquiry_id.siblings_line.ids))],'enrollment_num':enroll})
                                        for sib in stud_id.enquiry_id.siblings_line:
                                            enrollment_num = sib.enq_enroll
                                            if enrollment_num:
                                                student_record = self.env['pappaya.student'].search([('enrollment_num', '=', enrollment_num)])
                                                if student_record:
                                                    student_record.sudo().write({'siblings_ids': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})

                                                else:
                                                    enquiry_details = self.env['pappaya.enquiry'].search([('name', '=', enrollment_num)])
                                                    if enquiry_details:
                                                        enquiry_details.sudo().write({'siblings_line': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})
                                else:
                                    rec.total_paid += remaing_amount
                                    amt = 0.00
                                    amt =  remaing_amount
                                    remaing_amount -= remaing_amount
                                    if amt > 0.00:
                                        fees_receipt_line_list.append((0, 0, {
                                                                'name':rec.name,
                                                                'term_divide':rec.term_divide,
                                                                'amount':amt,
                                                                'concession_amount':rec.concession_amount
                                                                 
                                                     }))
                                    if rec.amount == rec.total_paid or rec.due_amount == 0.00:
                                        rec.term_state = 'paid'
                                    if not record.enquiry_id.state == 'done':
                                        record.sudo().enquiry_id.state = 'done'
                                        record.enquiry_id.stud_id.sudo().write({'state':'done'})
                                        
                                        
                                    if not record.student_id:
                                        valss = record.enquiry_id.get_student_vals()
                                        stud_id = self.env['pappaya.student'].sudo().create(valss)
                                        self.sudo().write({'student_id': stud_id.id})
                                        record.sudo().enquiry_id.stud_id = stud_id.id
                                        record.sudo().enquiry_id.enrollment_number = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        self.enrollment_number =  str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        enroll = str(school_code) + str(enquiry_mode_code) + str(academic_year) + str(stu_enr_se_no)
                                        stud_id.sudo().write({'siblings_ids': [(6,0, list(stud_id.enquiry_id.siblings_line.ids))],'enrollment_num':enroll})
                                        for sib in stud_id.enquiry_id.siblings_line:
                                            enrollment_num = sib.enq_enroll
                                            if enrollment_num:
                                                student_record = self.env['pappaya.student'].search([('enrollment_num', '=', enrollment_num)])
                                                if student_record:
                                                    student_record.sudo().write({'siblings_ids': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})

                                                else:
                                                    enquiry_details = self.env['pappaya.enquiry'].search([('name', '=', enrollment_num)])
                                                    if enquiry_details:
                                                        enquiry_details.sudo().write({'siblings_line': [(0,0, {'enq_enroll':enroll,'sibling_name': record.enquiry_id.student_first_name,'father_name':record.enquiry_id.father_name,'dob':record.enquiry_id.date_of_birth,'sibling_class':record.enquiry_id.grade_id.name})]})
                            record.enquiry_id.stud_id.sudo().write({'state':'done'})                          
            fee_ledger_line = []
            #fees_receipt_line_list = []
            for rec1 in self.fees_collection_line:
                fee_ledger_line.append((0, 0, {
                                                'name':rec1.name,
                                                'credit':rec1.amount,
                                                'concession_amount':rec1.concession_amount,
                                                'concession_type_id':rec1.concession_type_id.id,
                                                'debit':rec1.total_paid,
                                                'balance':rec1.amount - (rec1.total_paid + rec1.concession_amount),
                                                }))
            receipt = receipt_obj.sudo().create({
                                             'state':'paid',
                                             'fee_collection_id':record.id,   
                                             'society_id': record.society_id.id,
                                             'school_id' : record.school_id.id,
                                             'academic_year_id' : record.academic_year_id.id,
                                             'enrollment_number' : record.enrollment_number,
                                             'grade_id' : record.grade_id.id,
                                             'student_id' : record.student_id.id,
                                             'enquiry_id':record.enquiry_id.id,
                                             'pay_due_total':pay_due_total,
                                             'payment_mode': record.payment_mode,
                                             'cheque_dd' : record.cheque_dd,
                                             'bank_name':record.bank_name,
                                             'remarks':record.remarks,
                                             'receipt_date':self.collection_date,
                                             'fees_receipt_line':fees_receipt_line_list,
                                             'receipt_status':'uncleared'
                                           })
            if receipt.payment_mode == 'cash':
                receipt.write({'receipt_status': 'cleared','is_select':True})
            record.pay_amount=0.0
            record.payment_mode = ''
            record.cheque_dd = ''
            record.bank_name = ''
            record.remarks = False
            for fees_line in record.fees_collection_line:
                if fees_line.term_state == 'due':
                    fees_line.pay = False
            
            if receipt:
                led_obj_ref = ledger_obj.search([('enquiry_id', '=', receipt.enquiry_id.id), ('grade_id', '=', receipt.grade_id.id), ('student_id', '=', receipt.student_id.id)])
                
                fee_receipt_pos_line = []
                if receipt.payment_mode == 'card':
                    fees_head = ''
                    paid_amount = 0.0
                    concession_amount = 0.0
                    for frl in receipt.fees_receipt_line:
                        fees_head += frl.name + ' '
                        paid_amount += frl.amount
                        concession_amount += frl.concession_amount
                    fee_receipt_pos_line.append((0, 0, {
                                                        'fees_receipt_id': receipt.id,
                                                        'name':receipt.name,
                                                        'date':receipt.receipt_date,
                                                        'fees_head':fees_head,
                                                        'actual_amount':receipt.pay_due_total,
                                                        'paid_amount':paid_amount,
                                                        'concession_amount':concession_amount,
                                                        'payment_mode':receipt.payment_mode,
                                                        'pos_percentage':float(pos_percentage[0]),
                                                        'pos_total':pos_total,
                                                        'remarks':receipt.remarks
                                                        }))
                if not led_obj_ref:
                    fee_receipt_ledger_line = []
                    
                    for frl in receipt.fees_receipt_line:
                        fee_receipt_ledger_line.append((0, 0, {
                                                            'fees_receipt_id': receipt.id,
                                                            'name':receipt.name,
                                                            'posting_date':receipt.receipt_date,
                                                            'fees_head':frl.name,
                                                            'transaction':receipt.remarks,
                                                            'concession_amount':frl.concession_amount,
                                                            'payment_mode':receipt.payment_mode,
                                                            'amount':frl.amount,
                                                            })) 
                    
                    
                    
                    
                    ledger = ledger_obj.sudo().create({
                             'fee_collection_id':record.id,
                             'society_id': record.society_id.id,
                             'school_id' : record.school_id.id,
                             'academic_year_id' : record.academic_year_id.id,
                             'enrollment_number' : receipt.enrollment_number,
                             'grade_id' : record.grade_id.id,
                             'student_id' : receipt.student_id.id,
                             'enquiry_id' : record.enquiry_id.id,
                             'fee_receipt_ledger_line':fee_receipt_ledger_line,
                             'fee_ledger_line':fee_ledger_line,
                             'fee_receipt_pos_line':fee_receipt_pos_line                                 
                            })  
                else:
                    fee_receipt_ledger_line = []
                    for frl in receipt.fees_receipt_line:
                        fee_receipt_ledger_line.append((0, 0, {
                                                            'name':receipt.name,
                                                            'posting_date':receipt.receipt_date,
                                                            'fees_head':frl.name,
                                                            'transaction':receipt.remarks,
                                                            'concession_amount':frl.concession_amount,
                                                            'payment_mode':receipt.payment_mode,
                                                            'amount':frl.amount,
                                                            }))    
                    for lbr in led_obj_ref:
                        lbr.student_id = receipt.student_id.id
                        lbr.enrollment_number = receipt.enrollment_number
                        lbr.fee_ledger_line.sudo().unlink()
                        lbr.fee_receipt_ledger_line = fee_receipt_ledger_line
                        lbr.fee_ledger_line = fee_ledger_line
                        lbr.fee_receipt_pos_line = fee_receipt_pos_line
            if remaing_amount:
                raise ValidationError('Please pay actual amount')
            # Sending Details through SMS
            sms = {}
            sms['society_ids'] = [(6,0,[self.society_id.id])]
            sms['company_ids'] = [(6,0,[self.school_id.id])]
            sms['grade_ids'] = [(6,0,[self.grade_id.id])]
            sms['category'] = 'student'
            sms['fees_message'] = 'Name : ' + (str(self.student_id.name) + ' ' + str(self.student_id.middle_name or '') + ' ' + str(self.student_id.last_name or '')) + '\n' + \
                                        'Enrollment No : ' + str(self.enrollment_number) + '\n' + \
                                        'Grade : ' + str(self.grade_id.name) + '\n' + \
                                        'Section : ' + str(self.student_id.batch_id.name) + '\n' + \
                                        'Paid Amount : ' + str(self.paid_total) + '\n' + \
                                        'Due Amount : ' + str(self.due_total)
            sms['is_fees_sms'] = True
            sms_id = self.env['pappaya.send.sms'].create(sms)
            sms_line = {}
            sms_line['send_sms_id'] = sms_id.id
            sms_line['choosen'] = True
            sms_line['student_id'] = self.student_id.id
            sms_line['enrollment_num'] = self.enrollment_number
            sms_line['grade_id'] = self.grade_id.id
            sms_line['section_id'] = self.student_id.batch_id.id if self.student_id.batch_id else ''
            sms_line['father_mobile_no'] = self.student_id.father_mobile_no if self.student_id.father_mobile_no else ''
            sms_line['mother_mobile_no'] = self.student_id.mother_mobile_no if self.student_id.mother_mobile_no else ''
            sms_line['fees_sms_status'] = 'sent'
            self.env['student.sms.list'].create(sms_line)
            sms_obj = self.env['pappaya.send.sms'].search([('id','=',sms_id.id)])
            # sms_obj.send_sms()
            self.collection_date = False
            form_view = self.env.ref('pappaya_fees.pappaya_fees_receipt_form')
            tree_view = self.env.ref('pappaya_fees.pappaya_fees_receipt_tree')
            value = {
                'domain': str([('id', '=', receipt.id)]),
                'view_type': 'form',
                'view_mode': 'form',
                'name':'Fee receipt',
                'res_model': 'pappaya.fees.receipt',
                'view_id': False,
                'views': [(form_view and form_view.id or False, 'form'),
                           (tree_view and tree_view.id or False, 'tree')],
                'type': 'ir.actions.act_window',
                'res_id': receipt.id,
                'target': 'new',
                'nodestroy': True
             } 
            return value
        

    @api.model
    def create(self, vals):
        if 'student_id' in vals:
            sequence = self.env['ir.sequence'].next_by_code('pappaya.fees.collection')
            stu = self.env['pappaya.student'].browse(vals['student_id'])
            vals['enrollment_number'] = stu.enrollment_num
            vals['name'] = sequence or '/'
        res = super(Pappaya_fees_collection, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        if 'student_id' in vals:
             stu = self.env['pappaya.student'].browse(vals['student_id'])
             vals['enrollment_number'] = stu.enrollment_num

        res = super(Pappaya_fees_collection, self).write(vals)
        return res
    
    @api.one
    def copy(self, default=None):
        raise ValidationError("You are not allowed to Duplicate")  

class StudentFeesCollectionLine(models.Model):
    _name = 'student.fees.collection'
    
    pay = fields.Boolean('Pay')
    name = fields.Char('Fees Head')
    concession_type_id = fields.Many2one('pappaya.concession.type', 'Concession Type')
    # ~ term_divide = fields.Char('Term No')
    term_divide = fields.Selection([('1', 'Term-1'), ('2', 'Term-2'), ('3', 'Term-3'), ('4', 'Term-4'), ('5', 'Term-5'), ('6', 'Term-6'), ('7', 'Term-7'), ('8', 'Term-8'), ('9', 'Term-9'), ('10', 'Term-10')], string='Term No')
    partial_payment = fields.Boolean('Partial Payment')
    amount = fields.Float('Amount')
    concession_amount = fields.Float('Concession')
    concession_applied = fields.Boolean('Concession Applied')
    # ~ paid_amount = fields.Float('Paid Amount')
    due_amount = fields.Float('Due Amount', compute='calculate_due')
    refund_amount = fields.Float('Refund Amount')
    total_paid = fields.Float('Total Paid')
    term_state = fields.Selection([('due', 'Due'), ('paid', 'Paid'), ('refund', 'Transferred'),('fee_refund','Refund')], 'Status')
    collection_id = fields.Many2one('pappaya.fees.collection', 'Collection')

    @api.multi
    @api.depends('amount', 'due_amount')
    def calculate_due(self): 
        for line in self: 
            line.due_amount = line.amount - line.concession_amount - line.total_paid

#~ class StudentFeesCollectionBulkLine(models.Model):
    #~ _name = 'student.fees.bulk.line'
    
    #~ name = fields.Char('Fees Head')
    #~ term_divide = fields.Selection([('1', 'Term-1'), ('2', 'Term-2'), ('3', 'Term-3'), ('4', 'Term-4'), ('5', 'Term-5'), ('6', 'Term-6'), ('7', 'Term-7'), ('8', 'Term-8'), ('9', 'Term-9'), ('10', 'Term-10')], string='Term No')
    #~ amount = fields.Float('Amount')
    #~ concession_amount = fields.Float('Concession')
    #~ collection_id = fields.Many2one('pappaya.fees.collection', 'Collection')
    
    
    
