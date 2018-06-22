# -*- coding: utf-8 -*-
import time
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError, UserError
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT
import xlwt
import cStringIO
import base64
from openerp.http import request
from datetime import datetime, date
from cStringIO import StringIO
from datetime import date
import datetime
from datetime import timedelta
import pytz
import os
from PIL import Image
from xlwt import *


class FeeStructureReport(models.TransientModel):
    _name = 'fee.structure.report'

    society_ids = fields.Many2many('res.company', 'society_fee_structure_report_rel', 'company_id', 'society_id', string='Society')
    school_ids = fields.Many2many('res.company','school_fee_structure_report_rel','company_id','school_id', string='School')
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    
    
    
        
    @api.onchange('society_ids')
    def _onchange_society_ids(self):
        if self.society_ids:
            self.school_ids = []
            return {'domain': {'school_ids': [('type', '=', 'school'),('parent_id', 'in', self.society_ids.ids)]}}

    @api.multi
    def get_school_header(self):
        school_list = []
        if (len(self.school_ids) == 1 and len(self.society_ids) == 1) or (len(self.school_ids) == 1 and not self.society_ids):
            vals = {}
            vals['school_id'] = self.school_ids.name
            vals['logo'] = self.school_ids.logo if self.school_ids.logo else ''
            vals['street'] = self.school_ids.street if self.school_ids.street else ''
            vals['street2'] = self.school_ids.street2 if self.school_ids.street2 else ''
            vals['city'] = self.school_ids.city if self.school_ids.city else ''
            vals['zip'] = self.school_ids.zip if self.school_ids.zip else ''
            vals['phone'] = self.school_ids.phone if self.school_ids.phone else ''
            vals['fax'] = self.school_ids.fax_id if self.school_ids.fax_id else ''
            vals['email'] = self.school_ids.email if self.school_ids.email else ''
            vals['website'] = self.school_ids.website if self.school_ids.website else ''
            school_list.append(vals)
        if (len(self.society_ids) == 1 and not self.school_ids):
            vals = {}
            vals['school_id'] = self.society_ids.name
            vals['logo'] = self.society_ids.logo
            vals['street'] = self.society_ids.street if self.society_ids.street else ''
            vals['street2'] = self.society_ids.street2 if self.society_ids.street2 else ''
            vals['city'] = self.society_ids.city if self.society_ids.city else ''
            vals['zip'] = self.society_ids.zip if self.society_ids.zip else ''
            vals['phone'] = self.society_ids.phone if self.society_ids.phone else ''
            vals['fax'] = self.society_ids.fax_id if self.society_ids.fax_id else ''
            vals['email'] = self.society_ids.email if self.society_ids.email else ''
            vals['website'] = self.society_ids.website if self.society_ids.website else ''
            school_list.append(vals)
        if (len(self.society_ids) == 1 and len(self.school_ids) != 1):
            vals = {}
            vals['school_id'] = self.society_ids.name
            vals['logo'] = self.society_ids.logo
            vals['street'] = self.society_ids.street if self.society_ids.street else ''
            vals['street2'] = self.society_ids.street2 if self.society_ids.street2 else ''
            vals['city'] = self.society_ids.city if self.society_ids.city else ''
            vals['zip'] = self.society_ids.zip if self.society_ids.zip else ''
            vals['phone'] = self.society_ids.phone if self.society_ids.phone else ''
            vals['fax'] = self.society_ids.fax_id if self.society_ids.fax_id else ''
            vals['email'] = self.society_ids.email if self.society_ids.email else ''
            vals['website'] = self.society_ids.website if self.society_ids.website else ''
            school_list.append(vals)
        return school_list

    @api.multi
    def get_society_header(self):
        society_list = []
        if not self.society_ids and not self.school_ids:
            soc_list = ''
            obj = self.env['res.company'].search([('type', '=', 'society')])
            for record in obj:
                soc_list += str(record.name) + ', '
            vals = {}
            vals['society_id'] = soc_list[:-2]
            society_list.append(vals)
        else:
            sc_list = ''
            for record in self.society_ids:
                sc_list += str(record.name) + ', '
            vals = {}
            vals['society_id'] = sc_list[:-2]
            society_list.append(vals)
        return society_list

    @api.multi
    def get_data(self):
        
        domain = []
        student_domain = []
        data=[]
        if self.society_ids:
            domain.append(('society_ids','in',self.society_ids.ids))
        if self.school_ids:
            domain.append(('school_ids','in',self.school_ids.ids))
        if self.academic_year_id:
            domain.append(('academic_year_id','=', self.academic_year_id.id))
            
        fee_structure_sr = self.env['pappaya.fees.structure'].search(domain)
        
        data=[]
        
        for fee_structure in fee_structure_sr:
            #school_list = []
            for school in fee_structure.school_ids:
                
                if school.id in self.school_ids.ids :
            
                    class_list = []
                    class_merge = 0
                    type_merge = 0
                    
                    school_adm_total = school_reg_total = school_tut_total = 0.00
                    
                    
                    for class_id in fee_structure.grade_ids_m2m:
                        type_list = []
                        adm = 0.00
                        reg = 0.00
                        tut = 0.00
                        class_merge = 0
                        for type_name in ['ONE TIME','TERM']:
                            row_data = []
                            type_merge = 0
                            term_count = 0
                            for term in fee_structure.fee_term_line:
                                if type_name == 'ONE TIME' and 'Reg' in term.name:
                                    row_data.append({
                                                        'head':'',
                                                        'reg': term.amount,
                                                        'adm':0.00,
                                                        'tut':0.00
                                                    })
                                    reg += term.amount
                                    school_reg_total += reg
                                    
                                if type_name == 'ONE TIME' and 'Adm' in term.name:
                                    row_data.append({
                                                        'head':'',
                                                        'reg':0.00,
                                                        'adm':term.amount,
                                                        'tut':0.00
                                                    })
                                    adm += term.amount
                                    school_adm_total += adm
                                    
                                    
                                if type_name == 'TERM' and 'Adm' not in term.name and 'Reg' not in term.name and term.term_divide:
                                    term_count += 1
                                    row_data.append({
                                                        'head':'TERM '+ str(term_count),
                                                        'reg':0.00,
                                                        'adm':0.00,
                                                        'tut':term.amount
                                                    })
                                    tut += term.amount
                                    school_tut_total += tut
                            class_merge += len(row_data)
                            type_merge += len(row_data)
                            if type_merge:
                                type_list.append({
                                            'type_name': type_name,
                                            'type_merge':type_merge,     
                                            'row':row_data
                                    })        
                        if class_merge:            
                            class_list.append({
                                                'class_name':class_id.name,
                                                'class_merge':class_merge,
                                                'class_data':type_list,
                                                'reg_total':reg,
                                                'adm_total':adm,
                                                'tut_total':tut
                                                })
                        
                 
                    if len(class_list) > 0:
                        data.append({
                                        'class': class_list,
                                        'school':school.name,
                                        'academic_year':self.academic_year_id.name,
                                        'grand_reg':school_reg_total,
                                        'grand_adm':school_adm_total,
                                        'grand_tut':school_tut_total
                                             
                                
                                })
            #data.append(school_list)
        print data,"12344444444444444444444444444444444444444444444"
        return data
    
    

    @api.multi
    def generate_pdf_report(self):
        if not self.get_data():
            raise ValidationError(_("No record found..!"))
        return self.env['report'].get_action(self, 'pappaya_fees.generate_fee_structure_pdf_report')
    
    
    
    
    
