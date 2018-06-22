# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
from datetime import datetime


class PappayaFeesConcession(models.Model):
    _name ='pappaya.fees.concession'
    _rec_name = 'concession_type_id'
    
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
    
    concession_type_id = fields.Many2one('pappaya.concession.type','Concession Type', required=True)
    society_id = fields.Many2one('res.company','Society', default=_default_society)
    school_id = fields.Many2one('res.company', 'School', default=_default_school)
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    grade_id = fields.Many2one('pappaya.grade', 'Class', required=1)
    enrollment_number = fields.Char('Enrollment Number',related='student_id.enrollment_num')
    concession_head_line = fields.One2many('concession.head.line','concession_id','Concession Head Line')
    concession_applied_now = fields.Boolean('Applied')
    student_id = fields.Many2one('pappaya.student', 'Student', required=1)
    enquiry_mode = fields.Selection([('normal', 'Normal'), ('rte', 'RTE')])
    reason= fields.Text('Remarks')
    total = fields.Integer('Total')
    state = fields.Selection([('draft', 'Draft'), ('requested', 'Requested'), ('approved', 'Approved'),('applied','Applied'),('cancelled','Cancelled'),('rejected', 'Rejected')],
            string='Status', readonly=True, default='draft')
    rte_fee_exempted = fields.Boolean('Full Waiver Under RTE?')
    siblings_line = fields.Many2many('pappaya.siblings', 'sibling_concession_id_rel','concession_id', 'sibling_id','Siblings Details')
    staff_line = fields.Many2many('res.partner', 'staff_concession_id_rel','concession_id', 'staff_id','Staff Details')
    concession_code = fields.Char('Code',size=6)
    
    
    @api.one
    @api.constrains('concession_type_id', 'student_id')
    def _check_unique_record(self):
        if self.student_id:
            if len(self.search([('school_id', '=', self.school_id.id), ('society_id', '=', self.society_id.id), ('student_id', '=', self.student_id.id), ('grade_id', '=', self.grade_id.id), ('state', '=', 'draft')])) > 1:
                raise ValidationError("Record already exits in Draft status. please click on Discard button to proceed")
    
    
    @api.constrains('concession_head_line')
    def cononchange_con_line(self):
        
        if not self.concession_head_line:
            raise ValidationError(_("Please verify fees collection details for student (%s).") %(self.student_id.name))
        
        any_one_head_input = False
        if not self.concession_type_id.fees_head_ids:
            raise ValidationError(_("The configure fees head in Concession Type (%s).") %(self.concession_type_id.code))
        for rec in self.concession_head_line:
            if rec.discount_method == 'fix':
                any_one_head_input = True
                if rec.amount < rec.discount_amount:
                    raise ValidationError("Concession amount cannot be greater than actual amount")
            if rec.discount_method == 'per':
                any_one_head_input = True
                if rec.discount_amount > 100:
                    raise ValidationError("Percentage cannot be greater than 100")
        if self.concession_head_line and not any_one_head_input:
            raise ValidationError("Please select at least one concession mode")
        
#         adm_fees = False
#         tuition_fees = False
#         if not self.rte_fee_exempted:
#             for rec in self.concession_head_line:
#                 if rec.discount_method:
#                     if not rec.concession_applied and 'Adm' in rec.name and (rec.discount_method == 'fix' or rec.discount_method == 'per'):
#                         adm_fees = True
#                     if not rec.concession_applied and rec.term_divide and (rec.discount_method == 'fix' or rec.discount_method == 'per'):
#                         tuition_fees = True
#             if adm_fees and tuition_fees:
#                 raise ValidationError("Same concession type is not allowed for admission fees and tuition fees")
            
        collection_details = self.env['pappaya.fees.collection'].search([('student_id', '=', self.student_id.id),('grade_id', '=', self.grade_id.id),('school_id','=',self.school_id.id),('society_id','=',self.society_id.id),('academic_year_id','=',self.academic_year_id.id)])
        if not collection_details:
            raise ValidationError(_("Please update fees collection for student (%s).") %(self.student_id.name))
        collection_update = False
        for collection in collection_details:
            if collection.bulk_term_state == 'due':
                collection_update = True
        if not collection_update:
            raise ValidationError(_("Please verify fees collection details for student (%s).") %(self.student_id.name))
        
        for collect in collection_details:
            if collect.bulk_term_state =='due':
                for record_line in self.concession_head_line:
                    for rec in collect.fees_collection_line:
                        if not self.rte_fee_exempted:                
                            if not rec.term_state == 'paid' and record_line.name==rec.name and 'Adm' in rec.name and not (record_line.discount_method=='fix' or record_line.discount_method=='per'):
                                raise ValidationError("Please pay admission fees in order to proceed")
                        if self.rte_fee_exempted:                
                            if not rec.term_state == 'paid' and record_line.name==rec.name and 'Reg' in rec.name and not (record_line.discount_method=='fix' or record_line.discount_method=='per'):
                                raise ValidationError("Please pay registration fees in order to proceed")
                            if not rec.term_state == 'paid' and record_line.name==rec.name and 'Adm' in rec.name and not (record_line.discount_method=='fix' or record_line.discount_method=='per'):
                                raise ValidationError("Please pay admission fees in order to proceed")    
    
    
    @api.onchange('school_id')
    def onchange_school(self):
        self.academic_year_id = None
        if self.school_id:
            active_academic_year_id = self.env['academic.year'].search([('is_active','=', True),('school_id','in', self.school_id.id)])
            if active_academic_year_id:
                self.academic_year_id = active_academic_year_id[0].id
	    
    
    
    @api.onchange('grade_id')
    def onchange_grade(self):
        self.student_id = None
        self.concession_type_id = None
        self.concession_head_line = None
#         fee_head = self.env['pappaya.fees.structure'].search([('academic_year_id','=',self.academic_year_id.id),('grade_ids_m2m', 'in', self.grade_id.id),('school_ids','in',self.school_id.id)])
#         ids = []
#         if fee_head:
#             for i in fee_head:
#                 for h in i.fee_term_line:
#                     ids.append({
#                             'name':h.name,
#                             'term_divide':h.term_divide,
#                             'amount':h.amount,
#                             'readonly_state':'done',
#                             'concession_id': self.id        
#                         })
#             self.update({'concession_head_line':ids,})
    
    @api.onchange('concession_type_id')
    def onchange_concession_type_id(self):
        self.student_id = None
        self.concession_head_line = None
        
        if self.concession_type_id.code == 'SIBCON':
            self.concession_code = 'SIBCON'
            student_ids = self.env['pappaya.student'].search([('grade_id', '=', self.grade_id.id),('school_id', '=', self.school_id.id)])
            ids = []
            for student in student_ids:
                if student.siblings_ids:
                    ids.append(student.id)
                if student.enquiry_id.siblings_line:
                    ids.append(student.id)
                    
            return {'domain': {'student_id': [('id', 'in', ids)]}}
        
        elif self.concession_type_id.code == 'STFCON':
            self.concession_code = 'STFCON'
            staff_ids = self.env['staff.concession'].search([('grade_id', '=', self.grade_id.id),('school_id', '=', self.school_id.id)])
            ids = []
            for staff in staff_ids:
                if staff.student_id:
                    partner_active = self.env['res.partner'].search([('staff_code','=', staff.student_id.staff_code),('school_id', '=', self.school_id.id),('active','=', True)])
                    if partner_active:
                        ids.append(staff.student_id.id)
            return {'domain': {'student_id': [('id', 'in', ids)]}}
        elif self.concession_type_id and not self.concession_type_id.code == 'SIBCON' and not self.concession_type_id.code == 'STFCON':
            self.concession_code = None
            return {'domain': {'student_id': [('grade_id', '=', self.grade_id.id),('school_id', '=', self.school_id.id)]}}
        else:
            self.concession_code = None
            return {'domain': {'student_id': [('id', 'in', [])]}}
    
    
    @api.onchange('student_id')
    def onchange_enquiry_mode(self):
        if self.student_id:
            self.concession_head_line = None
            self.enquiry_mode = self.student_id.enquiry_mode
            self.rte_fee_exempted = self.student_id.enquiry_id.rte_fee_exempted
            collection_details = self.env['pappaya.fees.collection'].search([('student_id', '=', self.student_id.id),('grade_id', '=', self.grade_id.id),('school_id','=',self.school_id.id),('society_id','=',self.society_id.id),('academic_year_id','=',self.academic_year_id.id)])
            if self.concession_type_id.code == 'SIBCON':
                self.concession_code = 'SIBCON'
                self.siblings_line = [(6,0, list(self.student_id.siblings_ids.ids + self.student_id.enquiry_id.siblings_line.ids))]
            if self.concession_type_id.code == 'STFCON':
                self.concession_code = 'STFCON'
                staff_ids = self.env['res.partner'].search([('staff_code','=', self.student_id.staff_code),('school_id', '=', self.school_id.id),('active','=', True)])
                ids = []
                for staff in staff_ids:
                    if staff.student_detail_ids:
                        ids.append(staff.id)
                self.staff_line = [(6,0, ids)]
                    
            head_lines = []
            
            if not collection_details:
                self.concession_head_line = None
                #raise ValidationError(_("Please update fees collection for student (%s).") %(self.student_id.name))
            
            if collection_details:
                collection_update = False
                for collection in collection_details:
                    if collection.bulk_term_state == 'due':
                        collection_update = True
                if not collection_update:
                    self.concession_head_line = None
                    #raise ValidationError(_("Please verify fees collection details for student (%s).") %(self.student_id.name))        
                for collection in collection_details:
                    if collection.bulk_term_state == 'due':
                        self.concession_head_line = None
                        for line in collection.fees_collection_line:
                                allow_head = False
                                for head in self.concession_type_id.fees_head_ids:
                                    if head.name in line.name:
                                        allow_head = True
                                if line.term_state == 'due' and allow_head:
                                    head_lines.append({
                                                'name':line.name,
                                                'term_divide':line.term_divide,
                                                'amount':line.amount,
                                                'concession_id': self.id,
                                                'fee_due_amount':line.due_amount,
                                                'fee_term_state':line.term_state,
                                                'readonly_state':'draft'
                                                    })
                                else:
                                    head_lines.append({
                                                'name':line.name,
                                                'term_divide':line.term_divide,
                                                'amount':line.amount,
                                                'concession_id': self.id,
                                                'fee_due_amount':line.due_amount,
                                                'fee_term_state':line.term_state,
                                                'readonly_state':'done'
                                                            
                                            })
                        self.update({'concession_head_line':head_lines,})
            
                    

                    
    
#     @api.constrains('total')
#     def check_total(self):
#         if self.total > 100 and self.total != 0:
#             raise ValidationError("Please ensure concession percentage is not more than 100%")
    
    @api.onchange('concession_head_line','concession_head_line.line')
    def compute_total(self):
        tot = 0
        for line in self.concession_head_line:
            if line.discount_method  == 'per':
               tot += line.discount_amount
        self.total = tot
    
    @api.one
    def confirm_to_draft(self):
        self.state = 'draft'   

    
    @api.multi
    def confirm_request(self):
        collection_details = self.env['pappaya.fees.collection'].search([('student_id', '=', self.student_id.id),('grade_id', '=', self.grade_id.id),('school_id','=',self.school_id.id),('society_id','=',self.society_id.id),('academic_year_id','=',self.academic_year_id.id)])
        if not collection_details:
            raise ValidationError(_("Please update fees collection for student (%s).") %(self.student_id.name))
        if self.concession_type_id:
            for collect in collection_details:
                if collect.bulk_term_state =='due':
                    for record_line in self.concession_head_line:
                        if record_line.discount_method:
                            
                            for rec in collect.fees_collection_line:
                                if rec.name == record_line.name:
                                    if not self.rte_fee_exempted:
                                        if rec.term_state == 'paid' and not 'Reg' in rec.name and record_line.name==rec.name and (record_line.discount_method=='fix' or record_line.discount_method=='per'):
                                            raise ValidationError("Concession cannot be requested as the fees have been paid already")
                                        elif not rec.due_amount >= record_line.total_amount:
                                            raise ValidationError("concession amount cannot be greater than Due amount")
                                    else:
                                        if rec.term_state == 'paid' and record_line.name==rec.name and (record_line.discount_method=='fix' or record_line.discount_method=='per'):
                                            raise ValidationError("Concession cannot be requested as the fees have been paid already")
                                        elif not rec.due_amount >= record_line.total_amount:
                                            raise ValidationError("concession amount cannot be greater than Due amount")
            self.state = 'requested'
        else:
            raise ValidationError("Concession Type is not Selected")

        
        
    @api.multi
    def confirm_approved(self):
        self.state = 'approved'
    
    
    @api.multi
    def confirm_cancelled(self):
        collection_details = self.env['pappaya.fees.collection'].search([('student_id','=',self.student_id.id),('grade_id','=',self.grade_id.id),('school_id','=',self.school_id.id)])
        concession_details = self.env['student.fees.collection'].search([('collection_id','=',self.id)])
        for collect in collection_details:
            for line in collect.fees_collection_line:
                for conc in self.concession_head_line:
                    if not self.rte_fee_exempted:
                        if not 'Reg' in line.name and conc.name==line.name and line.concession_applied and conc.concession_applied:
                           line.concession_amount=0.0
                           line.concession_applied=False
                           line.concession_type_id=False
                           line.term_state = 'due'
                        fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id','=', collect.id)])
                        for ledger in fees_ledger:
                            for ledger_line in ledger.fee_ledger_line:
                                if not 'Reg' in line.name and line.name == ledger_line.name and line.name == conc.name:
                                    ledger_line.concession_type_id = False
                                    ledger_line.balance = ledger_line.balance + ledger_line.concession_amount
                                    ledger_line.concession_amount = 0.0
                    else:
                        if line.concession_applied and conc.concession_applied and conc.name==line.name:
                           line.concession_amount= 0.0
                           line.concession_applied=False
                           line.concession_type_id=False
                           line.term_state = 'due'
                        fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id','=', collect.id)])
                        for ledger in fees_ledger:
                            for ledger_line in ledger.fee_ledger_line:
                                if line.name == ledger_line.name and line.name == conc.name:
                                    ledger_line.concession_type_id = False
                                    ledger_line.balance = ledger_line.balance + ledger_line.concession_amount
                                    ledger_line.concession_amount = 0.0
                # for conc in self.concession_head_line:
                 #            if line.term_state == 'paid' and not 'Reg' in line.name and conc.name==line.name and (conc.discount_method=='fix' or conc.discount_method=='per'):
                #        raise ValidationError("Concession cannot be canceled as the fees have been paid already")
            self.state = 'cancelled'
    @api.one
    def confirm_rejected(self):
        self.state = 'rejected'
    
    
    @api.model
    def create(self, vals):
        if 'student_id' in vals:
            stu = self.env['pappaya.student'].browse(vals['student_id'])
            vals['enquiry_mode'] = stu.enquiry_mode
    	    vals['enrollment_number'] = stu.enrollment_num
            vals['rte_fee_exempted'] = stu.enquiry_id.rte_fee_exempted
            
            if vals.get('concession_code') == 'SIBCON':
                vals['siblings_line'] = [(6,0, list(stu.siblings_ids.ids))]
            elif vals.get('concession_code') == 'STFCON':
                staff_ids = self.env['res.partner'].search([('staff_code','=', stu.staff_code),('school_id', '=', vals.get('school_id'))])
                ids = []
                for staff in staff_ids:
                    if staff.student_detail_ids:
                        ids.append(staff.id)
                vals['staff_line'] = [(6,0, ids)]
            
        res = super(PappayaFeesConcession, self).create(vals)
        return res

   
   
    @api.multi
    def write(self, vals):
        if 'student_id' in vals:
            stu = self.env['pappaya.student'].browse(vals['student_id'])
            vals['enquiry_mode'] = stu.enquiry_mode
    	    vals['enrollment_number'] = stu.enrollment_num
            vals['rte_fee_exempted'] = stu.enquiry_id.rte_fee_exempted
            
            if vals.get('concession_code') == 'SIBCON':
                vals['siblings_line'] = [(6,0, list(stu.siblings_ids.ids))]
            elif vals.get('concession_code') == 'STFCON':
                staff_ids = self.env['res.partner'].search([('staff_code','=', stu.staff_code),('school_id', '=', vals.get('school_id'))])
                ids = []
                for staff in staff_ids:
                    if staff.student_detail_ids:
                        ids.append(staff.id)
                vals['staff_line'] = [(6,0, ids)]

        res = super(PappayaFeesConcession, self).write(vals)
        return res
    
    
    
    @api.constrains('student_id', 'enquiry_mode','concession_type_id')
    def _unique_concession_type(self):
        concession_type = False
        for record in self:
            if record.student_id.id:
                multi_concession = []
                if self.id:
                    multi_concession = self.env['pappaya.fees.concession'].search([('id','!=', self.id),('student_id', '=', record.student_id.id),('grade_id', '=', record.grade_id.id),('state','not in',('rejected','cancelled'))])
                else:
                    multi_concession = self.env['pappaya.fees.concession'].search([('student_id', '=', record.student_id.id), ('grade_id', '=', record.grade_id.id),('state','not in',('rejected','cancelled'))])
                if len(multi_concession) > 0:
                    current_head = False
                    previous_head = False
                    print multi_concession,"11111111111111111111111222222222222222"
                    for current_head_line in record.concession_head_line:
                        if current_head_line.discount_method:
                            for concession in multi_concession:
                                for previous_head_line in concession.concession_head_line:
                                    if not previous_head_line.term_divide and not current_head_line.term_divide and previous_head_line.concession_applied and current_head_line.name == previous_head_line.name:
                                        raise ValidationError(_("The selected fees head (%s) already applied concession to this student.") %(current_head_line.name))
                                    if previous_head_line.term_divide and previous_head_line.discount_method and previous_head_line.discount_amount:
                                        previous_head = True
                                    if current_head_line.term_divide and current_head_line.discount_method and current_head_line.discount_amount:
                                        current_head = True
                                    if current_head and previous_head:
                                        raise ValidationError(_("The selected fees head (Tuition Fees) already applied concession to this student."))
                                if  concession.concession_type_id.id == record.concession_type_id.id:
                                    raise ValidationError(_("The selected Concession Type (%s) already applied concession to this student.")%(str(record.concession_type_id.name)))
                else:
                    print "bbb2222222222222"
                    main_head = False
                    duplicate_head = False
                    main_count = 0
                    tution_count = 0
                    for current_head_line in record.concession_head_line:
                        
                        if not current_head_line.term_divide and current_head_line.discount_method and current_head_line.discount_amount:
                            main_count += 1
                            
                            main_head = True
                        print main_count,"main_head"
                        if main_count > 1:
                            raise ValidationError(_("Please apply concession to only one head"))
                        
                        if current_head_line.term_divide and current_head_line.discount_method and current_head_line.discount_amount:
                            tution_count += 0
                            duplicate_head = True
                        if main_count > 1:
                            raise ValidationError(_("Please apply concession to only one head"))
                            
                        if duplicate_head and main_head:
                            raise ValidationError(_("Please apply concession to only one head"))        
                    
                    #if len(record.search([('student_id', '=', record.student_id.id), ('concession_type_id', '=', record.concession_type_id.id), ('grade_id', '=', record.grade_id.id),('state','not in',('rejected','cancelled'))])) > 1:
                        
    
    @api.multi
    def concession(self):
        ledger_obj = self.env['pappaya.fees.ledger']
        collection_details = self.env['pappaya.fees.collection'].search([('student_id', '=', self.student_id.id), ('grade_id', '=', self.grade_id.id),('school_id','=',self.school_id.id)])
        self.state = 'applied'
        for concess in self:
            for concess_term in concess.concession_head_line:
                if not self.rte_fee_exempted:
                    if 'Adm' in concess_term.name:
                        for collect in collection_details.fees_collection_line:
                            if 'Adm' in collect.name and collect.term_state == 'due':
                                # ~ concess.unique_head_id(concess_term.id)
                                if concess_term.discount_method:
                                    collect.write({'concession_amount':concess_term.total_amount, 'concession_applied':True, 'concession_type_id':concess.concession_type_id.id})
                                    concess_term.write({'concession_applied':True})
                                    
                                    fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id','=', collection_details.id)])
                                    for ledger in fees_ledger:
                                        for ledger_line in ledger.fee_ledger_line:
                                            if 'Adm' in ledger_line.name:
                                                ledger_line.concession_type_id = concess.concession_type_id.id
                                                ledger_line.concession_amount = ledger_line.concession_amount + concess_term.total_amount
                                                ledger_line.balance = ledger_line.balance - concess_term.total_amount
                                                
                                    if collect.due_amount == 0.0:
                                        collect.term_state = 'paid'
                                        collection_details.enquiry_id.state = 'admitted'
                                        self.student_id.sudo().write({'state':'admitted'})
                                    if self.enquiry_mode != 'rte':
                                        return True
                    else:
                        if concess_term.term_divide and concess_term.discount_method:
                            # ~ concess.unique_head_id(concess_term.id)
                            for collect in collection_details.fees_collection_line:                     
                                if collect.term_state == 'due' and collect.term_divide == concess_term.term_divide: 
                                    collect.write({'concession_amount':concess_term.total_amount, 'concession_applied':True, 'concession_type_id':concess.concession_type_id.id})
                                    concess_term.write({'concession_applied':True})
                                    
                                    fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id','=', collection_details.id)])
                                    for ledger in fees_ledger:
                                        for ledger_line in ledger.fee_ledger_line:
                                            if collect.name == ledger_line.name:
                                                ledger_line.concession_type_id = concess.concession_type_id.id
                                                ledger_line.concession_amount = ledger_line.concession_amount + concess_term.total_amount
                                                ledger_line.balance = ledger_line.balance - concess_term.total_amount
                                    
                                    if collect.due_amount == 0.0:
                                        collect.term_state = 'paid'
                                    if collect.term_divide == '1':
                                        collection_details.enquiry_id.state = 'done'
                                        self.student_id.sudo().write({'state':'done'})
                                    if self.enquiry_mode != 'rte' and self.enquiry_mode !='normal':
                                        return True
                else:
                    
                    if 'Reg' in concess_term.name:
                        for collect in collection_details.fees_collection_line:
                            if 'Reg' in collect.name and collect.term_state == 'due':
                                # ~ concess.unique_head_id(concess_term.id)
                                if concess_term.discount_method:
                                    collect.write({'concession_amount':concess_term.total_amount, 'concession_applied':True, 'concession_type_id':concess.concession_type_id.id})
                                    concess_term.write({'concession_applied':True})
                                    
                                    fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id','=', collection_details.id)])
                                    for ledger in fees_ledger:
                                        for ledger_line in ledger.fee_ledger_line:
                                            if 'Reg' in ledger_line.name:
                                                ledger_line.concession_type_id = concess.concession_type_id.id
                                                ledger_line.concession_amount = ledger_line.concession_amount + concess_term.total_amount
                                                ledger_line.balance = ledger_line.balance - concess_term.total_amount
                                                
                                    if collect.due_amount == 0.0:
                                        collect.term_state = 'paid'
                                        collection_details.enquiry_id.state = 'reg_process'
                                        
                                    if not fees_ledger:
                                        fee_ledger_line = []
                                        #fees_receipt_line_list = []
                                        for rec1 in collection_details.fees_collection_line:
                                            fee_ledger_line.append((0, 0, {
                                                                            'name':rec1.name,
                                                                            'credit':rec1.amount,
                                                                            'concession_amount':rec1.concession_amount,
                                                                            'concession_type_id':rec1.concession_type_id.id,
                                                                            'debit':rec1.total_paid,
                                                                            'balance':rec1.amount - (rec1.total_paid + rec1.concession_amount),
                                                                            }))
                                        ledger = ledger_obj.sudo().create({
                                                                             'fee_collection_id':collection_details.id,
                                                                             'society_id': self.society_id.id,
                                                                             'school_id' : self.school_id.id,
                                                                             'academic_year_id' : self.academic_year_id.id,
                                                                             'enrollment_number' : self.enrollment_number,
                                                                             'grade_id' : self.grade_id.id,
                                                                             'student_id' : self.student_id.id,
                                                                             'enquiry_id' : self.student_id.enquiry_id.id,
                                                                             'fee_ledger_line':fee_ledger_line                                 
                                                                            }) 
                                        
                            
                                                        
                    elif 'Adm' in concess_term.name:
                        for collect in collection_details.fees_collection_line:
                            if 'Adm' in collect.name and collect.term_state == 'due':
                                # ~ concess.unique_head_id(concess_term.id)
                                if concess_term.discount_method:
                                    collect.write({'concession_amount':concess_term.total_amount, 'concession_applied':True, 'concession_type_id':concess.concession_type_id.id})
                                    concess_term.write({'concession_applied':True})
                                    
                                    fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id','=', collection_details.id)])
                                    for ledger in fees_ledger:
                                        for ledger_line in ledger.fee_ledger_line:
                                            if 'Adm' in ledger_line.name:
                                                ledger_line.concession_type_id = concess.concession_type_id.id
                                                ledger_line.concession_amount = ledger_line.concession_amount + concess_term.total_amount
                                                ledger_line.balance = ledger_line.balance - concess_term.total_amount
                                                
                                    if collect.due_amount == 0.0:
                                        collect.term_state = 'paid'
                                        collection_details.enquiry_id.state = 'admitted'
                                        self.student_id.sudo().write({'state':'admitted'})
                                    if self.enquiry_mode != 'rte':
                                        return True
                    else:
                        if concess_term.term_divide and concess_term.discount_method:
                            # ~ concess.unique_head_id(concess_term.id)
                            for collect in collection_details.fees_collection_line:                     
                                if collect.term_state == 'due' and collect.term_divide == concess_term.term_divide: 
                                    collect.write({'concession_amount':concess_term.total_amount, 'concession_applied':True, 'concession_type_id':concess.concession_type_id.id})
                                    concess_term.write({'concession_applied':True})
                                    
                                    fees_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id','=', collection_details.id)])
                                    for ledger in fees_ledger:
                                        for ledger_line in ledger.fee_ledger_line:
                                            if collect.name == ledger_line.name:
                                                ledger_line.concession_type_id = concess.concession_type_id.id
                                                ledger_line.concession_amount = ledger_line.concession_amount + concess_term.total_amount
                                                ledger_line.balance = ledger_line.balance - concess_term.total_amount
                                    
                                    if collect.due_amount == 0.0:
                                        collect.term_state = 'paid'
                                    if collect.term_divide == '1':
                                        collection_details.enquiry_id.state = 'done'
                                        self.student_id.sudo().write({'state':'done'})
                                    if self.enquiry_mode != 'rte' and self.enquiry_mode !='normal':
                                        return True         
                         
    
    #~ @api.multi
    #~ def unique_head_id(self,v):
         #~ if self.enquiry_mode == 'normal':
            #~ if self.student_id.id:
               #~ con=self.env['pappaya.fees.concession'].search([('student_id','=',self.student_id.id),('grade_id','=',self.grade_id.id)])
               #~ for j in con:
                   #~ for i in j.concession_head_line:
                       #~ if i.concession_applied and i.term_divide == v:
                          #~ raise ValidationError("The selected fees head has already been applied to this concession")
            
       


class ConcessionHeadLine(models.Model):
    _name = 'concession.head.line'
    
    #~ head_id = fields.Many2one('pappaya.fees.head','Fees Head')
    name = fields.Char('Fees Head')
    term_divide = fields.Selection([('1', 'Term-1'), ('2', 'Term-2'),('3','Term-3'),('4','Term-4'),('5','Term-5'),('6','Term-6'),('7','Term-7'),('8','Term-8'),('9','Term-9'),('10','Term-10')], string='Term No')
    amount = fields.Float('Amount')
    discount_method = fields.Selection([('fix', 'Amount'), ('per', 'Percentage')], 'Concession Mode')
    discount_amount = fields.Float('Amount / Percentage')
    total_amount = fields.Float('Concession Amount', compute='calculate_discount')
    concession_applied = fields.Boolean('Concession Applied')
    concession_id = fields.Many2one('pappaya.fees.concession','Concession')
    readonly_state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], 'Status')
    fee_due_amount = fields.Float('Fee Due Amount')
    fee_term_state = fields.Selection([('due', 'Due'), ('paid', 'Paid'), ('refund', 'Transferred')], 'Status')
    
    
    
    @api.constrains('discount_amount')
    def _check_pay_amount(self):
        if self.discount_amount < 0:
            raise ValidationError(_("The value of amount should be positive"))
        
#     @api.onchange('discount_method')
#     def _onchange_discount_method(self):
#         self.discount_amount = None
                
        
    @api.constrains('discount_method','discount_amount')
    def _check_pay_amount(self):
        if self.discount_method:
            if self.discount_amount == 0.00:
                raise ValidationError(_("Please Enter Amount / Percentage "))
        if not self.discount_method and self.discount_amount:
            raise ValidationError(_("Please select Concession Mode "))
        if self.discount_method and not self.discount_amount:
            raise ValidationError(_("Please Enter Amount / Percentage "))
    
    
#     @api.onchange('discount_method')
#     def onchange_discount_method(self):
#         self.discount_amount = 0.00
    
    @api.multi
    @api.depends('discount_amount','discount_method')
    def calculate_discount(self):
        for rec in self:
            if rec.discount_method == 'fix':
                rec.total_amount = rec.discount_amount
            elif rec.discount_method  == 'per':
                rec.total_amount =rec.amount*rec.discount_amount/100
                
                
                
    
    
    
    
