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


class RtePayment_report(models.TransientModel):
    _name = 'rte.payment.report'

    society_ids = fields.Many2many('res.company', 'society_rte_payment_report_rel', 'company_id', 'society_id', string='Society')
    school_ids = fields.Many2many('res.company','school_rte_payment_report_rel','company_id','school_id', string='School')
    academic_year_id = fields.Many2one('academic.year', 'Academic Year')
    from_date = fields.Date('From Date',required=True)
    to_date = fields.Date('To Date',required=True)
    
    @api.onchange('from_date','to_date')
    def onchange_date(self):
        if self.from_date and self.from_date > time.strftime('%Y-%m-%d'):
            self.from_date = None
            raise ValidationError(_('From Date is in the future!'))
        elif self.to_date and self.to_date > time.strftime('%Y-%m-%d'):
            self.to_date = None
            raise ValidationError(_('To Date is in the future!'))
        elif self.to_date and self.from_date and self.from_date > self.to_date:
            raise ValidationError(_(' Check in To Date should be greater than the From Date!'))
        
    @api.onchange('school_ids')
    def onchange_school(self):
        self.academic_year_id = []
        if not self.society_ids:
            self.school_ids = []
        return {'domain': {'academic_year_id': [('school_id', 'in', self.school_ids.ids)]}}
            
    
    @api.onchange('society_ids')
    def _onchange_society_ids(self):
        if self.society_ids:
            self.school_ids = []
            self.academic_year_id = []
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
        if self.from_date and self.from_date > time.strftime('%Y-%m-%d'):
            self.from_date = None
            raise ValidationError(_('From Date is in the future!'))
        elif self.to_date and self.to_date > time.strftime('%Y-%m-%d'):
            self.to_date = None
            raise ValidationError(_('To Date is in the future!'))
        elif self.to_date and self.from_date and self.from_date > self.to_date:
            raise ValidationError(_(' Check in To Date should be greater than the From Date!'))
        
        domain = []
        student_domain = []
        data=[]
        if self.society_ids:
            domain.append(('society_id','in',self.society_ids.ids))
        if self.school_ids:
            domain.append(('school_id','in',self.school_ids.ids))
        if self.academic_year_id:
            domain.append(('academic_year_id','=', self.academic_year_id.id))
            
        domain.append(('date','>=',self.from_date))
        domain.append(('date','<=',self.to_date))
        
        rte_reimbursment_sr = self.env['pappaya.rte.reimbursment'].search(domain)
        
        data=[]
        for reimbursment in rte_reimbursment_sr:
            if reimbursment.rte_fee_reimbursment:
                count = 0
                
                
                
                
                for line in reimbursment.rte_fee_reimbursment:
                    for stu in reimbursment.rte_students_list:
                        if line.grade_id.id == stu.grade_id.id:
                            count += 1
                            actual = book = dress = total = 0.00
                            if line.actual_fee:
                                actual = line.actual_fee 
                            if line.book_fee:
                                book = line.book_fee 
                            if line.dress_fees:
                                dress = line.dress_fees
                            if line.total_amt:
                                total +=  actual + book + dress      
                            adds = ''
                            
                            adds = stu.street 
                            if stu.street2:
                                adds += ', ' + stu.street2 
                            if stu.city:    
                                adds += ', ' + stu.city 
                            if stu.state_id.name:    
                                adds += ', ' +  stu.state_id.name 
                            if stu.zip:    
                                adds += ', ' + stu.zip
                            if stu.country_id.name: 
                                adds += ', ' + stu.country_id.name 
                            data.append({
                                        's_no': count,     
                                        'reg_no':stu.enquiry_id.rte_number,
                                        'school':stu.school_id.name,
                                        'f_mobile':stu.father_mobile_no,
                                        'addres':adds,
                                        'student':stu.full_name,
                                        'dob':stu.birth_date,
                                        'class':line.grade_id.name,
                                        'actual':actual,
                                        'book':book,
                                        'dress':dress,
                                        'total':total,
                                        'payment_date':reimbursment.date,
                                        'mode':reimbursment.payment_mode,
                                        'fees_head':''
                                        })
        return data
    
    @api.multi
    def from_data(self):
        workbook = xlwt.Workbook()
        company_name = xlwt.easyxf('font: name Times New Roman, height 350, bold on; align: wrap on, vert centre, horiz centre;')
        company_address = xlwt.easyxf('font: name Times New Roman, height 230, bold on; align: wrap on, vert centre, horiz centre;')
        header = xlwt.easyxf('font: name Times New Roman, height 200, bold on,italic off; align: wrap on, vert centre, horiz centre;  borders: top thin, bottom thin, left thin, right thin;')
        answer = xlwt.easyxf('font: name Times New Roman, height 200; borders: top thin, bottom thin, left thin, right thin;')
        
        answer_center = xlwt.easyxf('font: name Times New Roman, height 200; borders: top thin, bottom thin, left thin, right thin; align: wrap on, vert centre, horiz centre;')
        
        sheet_name = 'RTE Payment Report'
        sheet = workbook.add_sheet(sheet_name)
        sheet.row(0).height = 450;
        sheet.row(7).height = 450;
        sheet.row(8).height = 450;
        sheet.row(9).height = 550;
        
        style_header_without_border = XFStyle()        
        fnt = Font()
        fnt.bold = True
        fnt.height = 12*0x14
        style_header_without_border.font = fnt        
        al1 = Alignment()
        al1.horz = Alignment.HORZ_CENTER
        al1.vert = Alignment.VERT_CENTER        
        pat2 = Pattern()        
        style_header_without_border.alignment = al1
        style_header_without_border.pattern = pat2
        
        style_center_align_without_border = XFStyle()
        al_c = Alignment()
        al_c.horz = Alignment.HORZ_CENTER
        al_c.vert = Alignment.VERT_CENTER
        style_center_align_without_border.alignment = al_c
        
        row_no = 0
        
        # cwd = os.path.abspath(__file__)
        # path = cwd.rsplit('/', 2)
        # image_path = path[0] + '/static/src/img/dis_logo1.bmp'
        # image_path = image_path.replace("pappaya_fees", "pappaya_core")
        # sheet.write_merge(0,4,0,0,'',style_center_align_without_border)
        #
        # sheet.insert_bitmap(image_path, 0, 0, scale_x = .3, scale_y = .4)
        
        if (len(self.school_ids) == 1 and len(self.society_ids) == 1) or (len(self.school_ids) == 1 and not self.society_ids):
            sheet.write_merge(row_no, row_no, 0, 14, self.school_ids.name if self.school_ids.name else '', style_header_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14, (self.school_ids.street if self.school_ids.street else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14, (self.school_ids.street2 if self.school_ids.street2 else '') + ', ' +(self.school_ids.city if self.school_ids.city else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14, 'P.O Box: ' + (self.school_ids.street2 if self.school_ids.street2 else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14, 'Tel: ' + (self.school_ids.phone if self.school_ids.phone else '') + ', ' + 'Fax: ' + (self.school_ids.fax if self.school_ids.fax else '') + ', ' + 'Email: ' + (self.school_ids.email if self.school_ids.email else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14, self.school_ids.website if self.school_ids.website else '', style_center_align_without_border)
            row_no += 2
            sheet.write_merge(row_no, row_no, 0, 14, 'RTE Payment Report', company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'For the period of ' + datetime.datetime.strptime(str(self.from_date),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y") + ' To ' + datetime.datetime.strptime(str(self.to_date),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y"), answer_center)
        if (len(self.society_ids) == 1 and not self.school_ids) or (len(self.society_ids) == 1 and len(self.school_ids) > 1):
            sheet.write_merge(row_no, row_no, 0, 14, self.society_ids.name if self.society_ids.name else '',style_header_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14, (self.society_ids.street if self.society_ids.street else ''),style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,(self.society_ids.street2 if self.society_ids.street2 else '') + ', ' + (self.society_ids.city if self.society_ids.city else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'P.O Box: ' + (self.society_ids.street2 if self.society_ids.street2 else ''),style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,
                              'Tel: ' + (self.society_ids.phone if self.society_ids.phone else '') + ', ' + 'Fax: ' + (self.society_ids.fax if self.society_ids.fax else '') + ', ' + 'Email: ' + (self.society_ids.email if self.society_ids.email else ''),style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14, self.society_ids.website if self.society_ids.website else '',style_center_align_without_border)
            row_no += 2
            sheet.write_merge(row_no, row_no, 0, 14, 'RTE Payment Report', company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'For the period of ' + datetime.datetime.strptime(str(self.from_date),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y") + ' To ' + datetime.datetime.strptime(str(self.to_date),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y"), answer_center)
        if (not self.society_ids and not self.school_ids) or (len(self.school_ids) > 1 and not self.society_ids):
            soc_list = ''
            obj = self.env['res.company'].search([('type', '=', 'society')])
            for record in obj:
                soc_list += str(record.name) + ', '
            sheet.write_merge(row_no, row_no, 0, 14,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,soc_list[:-2],company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'')
            row_no += 2
            sheet.write_merge(row_no, row_no, 0, 14, 'RTE Payment Report', company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'For the period of ' + datetime.datetime.strptime(str(self.from_date),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y") + ' To ' + datetime.datetime.strptime(str(self.to_date),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y"), answer_center)
        if (len(self.society_ids) > 1) or (len(self.society_ids) > 1 and len(self.school_ids) > 1):
            sc_list = ''
            for record in self.society_ids:
                sc_list += str(record.name) + ', '
            sheet.write_merge(row_no, row_no, 0, 14,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14, sc_list[:-2],company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'')
            row_no += 2
            sheet.write_merge(row_no, row_no, 0, 14, 'RTE Payment Report', company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 14,'For the period of ' + datetime.datetime.strptime(str(self.from_date),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y") + ' To ' + datetime.datetime.strptime(str(self.to_date),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y"), answer_center)

        row_no = 9
        sheet.row(8).height = 350;
        sheet.col(0).width = 256 * 15
        sheet.write(row_no, 0, 'S.No', header)
        
        sheet.col(1).width = 256 * 15
        sheet.write(row_no, 1, 'School Name', header)
        
        sheet.col(2).width = 256 * 15
        sheet.write(row_no, 2, 'Registration No', header)
        sheet.col(3).width = 256 * 17
        sheet.write(row_no, 3, 'Student Name', header)
        
        sheet.col(4).width = 256 * 17
        sheet.write(row_no, 4, 'DOB', header)
        
        sheet.col(5).width = 256 * 34
        sheet.write(row_no, 5, 'Address', header)
        
        sheet.col(6).width = 256 * 17
        sheet.write(row_no, 6, 'Mobile', header)
        
        sheet.col(7).width = 256 * 17
        sheet.write(row_no, 7, 'Class Name', header)
        sheet.col(8).width = 256 * 17
        sheet.write(row_no, 8, 'Actual Fees', header)
        sheet.col(9).width = 256 * 17
        sheet.write(row_no, 9, 'Book Fees', header)
        
        sheet.col(10).width = 256 * 17
        sheet.write(row_no, 10, 'Dress Fees', header)
        
        sheet.col(11).width = 256 * 17
        sheet.write(row_no, 11, 'Total Fee', header)
        
        sheet.col(12).width = 256 * 17
        sheet.write(row_no, 12, 'Payment Date', header)
        
        sheet.col(13).width = 256 * 17
        sheet.write(row_no, 13, 'Mode of Payment (CHQ/DD/NEFT)', header)
        
        
        sheet.col(14).width = 256 * 17
        sheet.write(row_no, 14, 'Payment Details According to Payment Head', header)
        
        row_no += 1
        for data in self.get_data():
            sheet.write(row_no, 0, data['s_no'] , answer)
            sheet.write(row_no, 1, data['school'] or '' , answer)
            
            sheet.write(row_no, 2, data['reg_no'] or '' , answer)
            sheet.write(row_no, 3, data['student'] or '', answer)
            sheet.write(row_no, 4, datetime.datetime.strptime(str(data['dob']),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y") or '', answer)
            
            sheet.write(row_no, 5, data['addres'] or '', answer)
            sheet.write(row_no, 6, data['f_mobile'] or '', answer)
            
            sheet.write(row_no, 7, data['class'] or '', answer)
            sheet.write(row_no, 8, data['actual'] or '', answer)
            sheet.write(row_no, 9, data['book'] or '', answer)
            sheet.write(row_no, 10, data['dress'] or '', answer)
            sheet.write(row_no, 11, data['total'] or '', answer)
            sheet.write(row_no, 12, datetime.datetime.strptime(str(data['payment_date']),DEFAULT_SERVER_DATE_FORMAT).strftime("%d/%b/%Y") or '', answer)
            sheet.write(row_no, 13, data['mode'] or '', answer)
            sheet.write(row_no, 14, data['fees_head'] or '', answer)
            
            row_no += 1
        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data

    @api.multi
    def generate_pdf_report(self):
        if not self.get_data():
            raise ValidationError(_("No record found..!"))
        start_date = fields.Date.from_string(self.from_date)
        end_date = fields.Date.from_string(self.to_date)
        if start_date > end_date:
            raise ValidationError(_("To date should not be less than from date."))
        return self.env['report'].get_action(self, 'pappaya_fees.generate_rte_payment_pdf_report')
    
    @api.multi
    def generate_receipt_excel_report(self):
        if not self.get_data():
                raise ValidationError(_("No record found..!"))
        data = base64.encodestring(self.from_data())
        attach_vals = {
            'name':'%s.xls' % ('RTE Payment Report'),
            'datas':data,
            'datas_fname':'%s.xls' % ('RTE Payment Report'),
         }
        doc_id = self.env['ir.attachment'].create(attach_vals)
        return {
            'type': 'ir.actions.act_url',
            'url':'web/content/%s?download=true'%(doc_id.id),
            'target': 'self',
        }
    
    
    
    
