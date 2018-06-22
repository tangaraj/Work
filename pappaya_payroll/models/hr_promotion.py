# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
from datetime import datetime


class PappayaEmployeePromotion(models.Model):
    _name = 'pappaya.employee.promotion'
    _rec_name = "employee_name"
    
    @api.model
    def _default_start(self):
        return fields.Date.context_today(self)
    
    employee_name = fields.Many2one('hr.employee', 'Employee Name')
    department_id = fields.Many2one('hr.department', 'From Department')
    designation_id = fields.Many2one('hr.job', 'From Designation')
    to_department_id = fields.Many2one('hr.department', 'To Department')
    to_designation_id = fields.Many2one('hr.job', 'To Designation')
    description = fields.Text()
    promotion_history_ids = fields.One2many('pappaya.employee.promotion.history', 'history_id', string="History")
    date = fields.Date('Date', default=_default_start, readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('rejected', 'Rejected'), ('requested', 'Requested'), ('approved', 'Approved')], string="Status", default='draft')
    change_type = fields.Selection([('promotion', 'Promotion'), ('transfer', 'Transfer')], string="Internal Mobility", default='promotion')
    
    @api.onchange('employee_name')
    def onchange_employee_details(self):
        if self.employee_name:
            self.designation_id = self.employee_name.job_id.id
            self.department_id = self.employee_name.department_id.id
            
    @api.one
    def act_reject(self):
        approve_info = []
        if self.state == 'requested':
            self.state = 'rejected'
            approve_info.append({
                            'date':self.date,
                             'department_id':self.department_id.id,
                             'designation_id':self.designation_id.id,
                             'to_department_id':self.to_department_id.id,
                             'to_designation_id':self.to_designation_id.id,
                            'user_id':self.env.uid,
                            'updated_on':datetime.today().date(),
                            'status':self.state,
                            'employee_id':self.employee_name.id,
                            'change_type':self.change_type,
                             })
            self.update({'promotion_history_ids':approve_info})
    
    @api.multi
    def request_in_progress(self):
        approve_info = []
        if self.state == 'draft':
            self.state = 'requested'
            approve_info.append({
                            'date':self.date,
                             'department_id':self.department_id.id,
                             'designation_id':self.designation_id.id,
                             'to_department_id':self.to_department_id.id,
                             'to_designation_id':self.to_designation_id.id,
                            'user_id':self.env.uid,
                            'updated_on':datetime.today().date(),
                            'status':self.state,
                            'employee_id':self.employee_name.id,
                            'change_type':self.change_type,
                             })
            self.update({'promotion_history_ids':approve_info})
            
    @api.multi
    def act_approve(self):
        approve_info = []
        if self.state == 'requested' and self.employee_name:
            self.state = 'approved'
            self.employee_name.write({'department_id':self.to_department_id.id,
                                      'job_id':self.to_designation_id.id})
            
            approve_info.append({
                            'date':self.date,
                             'department_id':self.department_id.id,
                             'designation_id':self.designation_id.id,
                             'to_department_id':self.to_department_id.id,
                             'to_designation_id':self.to_designation_id.id,
                            'user_id':self.env.uid,
                            'updated_on':datetime.today().date(),
                            'status':self.state,
                            'employee_id':self.employee_name.id,
                            'change_type':self.change_type,
                             })
            self.update({'promotion_history_ids':approve_info})
            
    
class PappayaEmployeePromotionHistory(models.Model):
    _name = 'pappaya.employee.promotion.history'
    
    date = fields.Date()
    history_id = fields.Many2one('pappaya.employee.promotion')
    department_id = fields.Many2one('hr.department', 'From Department')
    designation_id = fields.Many2one('hr.job', 'From Designation')
    to_department_id = fields.Many2one('hr.department', 'To Department')
    to_designation_id = fields.Many2one('hr.job', 'To Designation')
    user_id = fields.Many2one('res.users', 'User')
    updated_on = fields.Date("Updated On")
    status = fields.Char()
    employee_id = fields.Many2one('hr.employee')
    change_type = fields.Selection([('promotion', 'Promotion'), ('transfer', 'Transfer')], string="Internal Mobility", default='promotion')
    
    
class hr_employee(models.Model):
    _inherit = 'hr.employee'
    
    employee_history_ids = fields.One2many('pappaya.employee.promotion.history', 'employee_id',)
    
