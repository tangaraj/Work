# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import except_orm, ValidationError
import re
from datetime import datetime


class Pappaya_pos_structure(models.Model):
    _name = 'pappaya.pos.structure'
    _rec_name = 'academic_year_id'
    
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
        
    
    
    @api.onchange('school_ids')
    def onchange_school(self):
        self.academic_year_id = []
        if not self.society_ids:
            self.school_ids = []
        return {'domain': {'academic_year_id': [('school_id', 'in', self.school_ids.ids)]}}
    
    @api.onchange('society_ids')
    def onchange_school_domain(self):
        if self.society_ids:
            self.school_ids = []
            self.academic_year_id = []
            return {'domain': {'school_ids': [('type', '=', 'school'),('parent_id', 'in', self.society_ids.ids)]}}
        

    society_ids =fields.Many2many('res.company','society_fee_pos_structure_rel','structure_id','society_id',string= 'Society')
    school_ids = fields.Many2many('res.company','fee_pos_structure_school_rel','structure_id','school_id', string='School')
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    pos_percentage = fields.Float('Percentage %')
    
    @api.constrains('pos_percentage')
    def pos_percentage_constrains(self):
        if self.pos_percentage == 0.00:
            raise ValidationError(_("Please enter valid Percentage "))
        if self.pos_percentage < 0:
            raise ValidationError(_("Please enter valid Percentage"))
        if self.pos_percentage:
            if 100 < self.pos_percentage:
                raise ValidationError(_("Please enter valid Percentage "))
    
    @api.one
    def copy(self, default=None):
        raise ValidationError("You are not allowed to Duplicate")          
            
    @api.constrains('society_ids','school_ids','academic_year_id')
    def pos_duplicate_constrains(self):
        if len(self.sudo().search([('society_ids','in', self.society_ids.ids),('school_ids','in', self.school_ids.ids),('academic_year_id', '=', self.academic_year_id.id)])) > 1 :
            raise ValidationError(_("Record already exits."))
                
                
    
 
    