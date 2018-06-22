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

class ClassWiseFeeReconciliation(models.TransientModel):
    _name = 'class.wise.feereconciliation'
    
    society_ids = fields.Many2many('res.company', 'society_rel_class_wise_feereconciliation', 'company_id', 'society_id', string='Society')
    school_ids = fields.Many2many('res.company','school_rel_class_wise_feereconciliation','company_id','school_id', string='School')
    academic_year_id = fields.Many2one('academic.year',required=True, string='Academic Year')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    
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
        
    @api.onchange('society_ids')
    def _onchange_society_ids(self):
        if self.society_ids:
            self.school_ids = []
            return {'domain': {'school_ids': [('type', '=', 'school'),('parent_id', 'in', self.society_ids.ids)]}}
            
    @api.onchange('school_ids')
    def _onchange_school_id(self):
        if self.school_ids:
            self.academic_year_id = None
            year_ids = self.academic_ids()
            return {'domain': {'academic_year_id': [('id', 'in', year_ids)]}}

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
    def academic_ids(self):
        date_list = []
        year_ids = []
        if self.school_ids:
            max_start_date = academic_year_id = self.env['academic.year'].sudo().search([('school_id', 'in', self.school_ids.ids)],order="start_date desc",limit=1).start_date
            min_start_date = academic_year_id = self.env['academic.year'].sudo().search([('school_id', 'in', self.school_ids.ids)],order="start_date",limit=1).start_date
            max_end_date = academic_year_id = self.env['academic.year'].sudo().search([('school_id', 'in', self.school_ids.ids)],order="end_date desc",limit=1).end_date
            min_end_date = academic_year_id = self.env['academic.year'].sudo().search([('school_id', 'in', self.school_ids.ids)],order="end_date",limit=1).end_date
            date_list.append(max_start_date)
            date_list.append(min_start_date)
            date_list.append(max_end_date)
            date_list.append(min_end_date)
            min_year = (datetime.datetime.strptime(min(date_list), DEFAULT_SERVER_DATE_FORMAT)).year
            max_year = (datetime.datetime.strptime(max(date_list), DEFAULT_SERVER_DATE_FORMAT)).year 
            academic_year_ids = self.env['academic.year'].sudo().search([('school_id', 'in', self.school_ids.ids)])
            for academic_year in  academic_year_ids:
                if (datetime.datetime.strptime(academic_year.start_date, DEFAULT_SERVER_DATE_FORMAT)).year >= min_year or (datetime.datetime.strptime(academic_year.start_date, DEFAULT_SERVER_DATE_FORMAT)).year <= max_year:
                    year_ids.append(academic_year.id)
            return year_ids
        if not self.school_id and self.society_id:
            school_ids= self.env['res.company'].search([('parent_id','in', self.society_ids.ids)]).ids
            max_start_date = academic_year_id = self.env['academic.year'].sudo().search([('school_id', 'in', school_ids)],order="start_date desc",limit=1).start_date
            min_start_date = academic_year_id = self.env['academic.year'].sudo().search([('school_id', 'in', school_ids)],order="start_date",limit=1).start_date
            max_end_date = academic_year_id = self.env['academic.year'].sudo().search([('school_id', 'in', school_ids)],order="end_date desc",limit=1).end_date
            min_end_date = academic_year_id = self.env['academic.year'].sudo().search([('school_id', 'in', school_ids)],order="end_date",limit=1).end_date
            date_list.append(max_start_date)
            date_list.append(min_start_date)
            date_list.append(max_end_date)
            date_list.append(min_end_date)
            min_year = (datetime.datetime.strptime(min(date_list), DEFAULT_SERVER_DATE_FORMAT)).year
            max_year = (datetime.datetime.strptime(max(date_list), DEFAULT_SERVER_DATE_FORMAT)).year 
            academic_year_ids = self.env['academic.year'].sudo().search([('school_id', 'in', school_ids)])
            for academic_year in  academic_year_ids:
                if (datetime.datetime.strptime(academic_year.start_date, DEFAULT_SERVER_DATE_FORMAT)).year >= min_year or (datetime.datetime.strptime(academic_year.start_date, DEFAULT_SERVER_DATE_FORMAT)).year <= max_year:
                    year_ids.append(academic_year.id)
            return year_ids

    @api.multi
    def get_data(self):
        student_domain = []
        data=[]
        input_school_ids = None
        if self.school_ids:
            input_school_ids = self.school_ids.ids
        elif self.society_ids:
            input_school_ids = self.env['res.company'].search([('type','=','school'),('parent_id','=',self.society_ids.ids)]).ids
        elif not self.school_ids and not self.society_ids:
            input_school_ids= self.env['res.company'].search([('type','=','school')]).ids
        
        class_ids = self.env['pappaya.grade'].search([])
        school_ids = self.env['res.company'].search([('type','=','school')])
        school_list = []
        
        for school in school_ids:
            for input_school in input_school_ids:
                if school.id == input_school:
                    total_stu_count = 0
                    total_open_dr = total_open_cr = total_charge = total_concession = total_collection = total_adj_dr = total_adj_cr = total_close_dr = total_close_cr = 0.00
                    s_no = 1
                    class_list = []
                    for class_id in class_ids:
                        class_record = False
                        domain = []
                        domain.append(('school_id','=',school.id))    
                        domain.append(('society_id','=',school.parent_id.id))
                        domain.append(('academic_year_id','=',self.academic_year_id.id))
                        domain.append(('grade_id','=',class_id.id))
                        domain.append(('active','=',True))
                        open_dr = open_cr = charge = concession = collection = adj_dr = adj_cr = close_dr = close_cr = 0.00
                        
                        stu_count = 0
                        collection_ids = self.env['pappaya.fees.collection'].search(domain).ids
                        student_ids = self.env['pappaya.student'].search(domain).ids
                        
                        fee_ledger = self.env['pappaya.fees.ledger'].search([('fee_collection_id','in', collection_ids),('student_id', 'in', student_ids)])
                        for ledger in fee_ledger:
                            class_record = True
                            for ledger_line in ledger.fee_ledger_line:
                                if 'Adm' in ledger_line.name or 'Reg' in ledger_line.name or 'Tui' in ledger_line.name:
                                    charge += ledger_line.credit
                                    collection += ledger_line.debit
                                else:
                                    adj_cr += ledger_line.credit
                                    adj_dr += ledger_line.debit
                                close_dr += ledger_line.balance
                                concession += ledger_line.concession_amount
                                        
                        #if class_record:
                        class_list.append({
                                            'class_name':class_id.name,
                                            'stu_count':len(fee_ledger),
                                            'open_dr':open_dr,
                                            'open_cr':open_cr,
                                            'charge':charge,
                                            'concession':concession,
                                            'collection':collection,
                                            'adj_dr':adj_dr,
                                            'adj_cr':adj_cr,
                                            'close_dr':close_dr,
                                            'close_cr':close_cr
                                            
                                            })
                        total_stu_count += len(fee_ledger)
                        total_open_dr += open_dr
                        total_open_cr += open_cr
                        total_charge += charge
                        total_concession += concession
                        total_collection += collection
                        total_adj_dr += adj_dr
                        total_adj_cr += adj_cr
                        total_close_dr += close_dr
                        total_close_cr += close_cr
                                
            if class_list:
                school_list.append({
                                        'school_name':school.name,
                                        'total_stu_count':total_stu_count,
                                        'total_open_dr': total_open_dr,
                                        'total_open_cr': total_open_cr,
                                        'total_charge': total_charge,
                                        'total_concession': total_concession,
                                        'total_collection': total_collection,
                                        'total_adj_dr': total_adj_dr,
                                        'total_adj_cr': total_adj_cr,
                                        'total_close_dr': total_close_dr,
                                        'total_close_cr' :total_close_cr,
                                        'class_s':class_list
                                    })
        if school_list:
            data.append({
                            'school_s':school_list
                        })
        return data
                    
                    
    def from_data(self):
        workbook = xlwt.Workbook()
        company_name = xlwt.easyxf('font: name Times New Roman, height 350, bold on; align: wrap on, vert centre, horiz centre;')
        company_address = xlwt.easyxf('font: name Times New Roman, height 230, bold on; align: wrap on, vert centre, horiz centre;')
        header = xlwt.easyxf('font: name Times New Roman, height 200, bold on,italic off; align: wrap on, vert centre, horiz centre;  borders: top thin, bottom thin, left thin, right thin;')
        header_left = xlwt.easyxf('font: name Times New Roman, height 200, bold on,italic off; align: wrap on, horiz left;  borders: top thin, bottom thin, left thin, right thin;')
        header_right = xlwt.easyxf('font: name Times New Roman, height 200, bold on,italic off; align: wrap on, horiz right;  borders: top thin, bottom thin, left thin, right thin;')
        
        answer = xlwt.easyxf('font: name Times New Roman, height 200; borders: top thin, bottom thin, left thin, right thin;')
        answer_center = xlwt.easyxf('font: name Times New Roman, height 200; borders: top thin, bottom thin, left thin, right thin; align: wrap on, vert centre, horiz centre;')
        
        
        sheet_name = 'Fee Reconciliation'
        sheet = workbook.add_sheet(sheet_name)
        sheet.row(0).height = 450; 
    
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
            sheet.write_merge(row_no, row_no, 0, 10, self.school_ids.name if self.school_ids.name else '', style_header_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, (self.school_ids.street if self.school_ids.street else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, (self.school_ids.street2 if self.school_ids.street2 else '') + ', ' +(self.school_ids.city if self.school_ids.city else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, 'P.O Box: ' + (self.school_ids.street2 if self.school_ids.street2 else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, 'Tel: ' + (self.school_ids.phone if self.school_ids.phone else '') + ', ' + 'Fax: ' + (self.school_ids.fax if self.school_ids.fax else '') + ', ' + 'Email: ' + (self.school_ids.email if self.school_ids.email else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, self.school_ids.website if self.school_ids.website else '', style_center_align_without_border)
            row_no += 3
            sheet.write_merge(row_no, row_no, 0, 10, 'Fee Reconciliation', company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, 'as on :' + time.strftime('%d/%m/%Y'), answer_center)
        if (len(self.society_ids) == 1 and not self.school_ids) or (len(self.society_ids) == 1 and len(self.school_ids) > 1):
            sheet.write_merge(row_no, row_no, 0, 10, self.society_ids.name if self.society_ids.name else '',style_header_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, (self.society_ids.street if self.society_ids.street else ''),style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,(self.society_ids.street2 if self.society_ids.street2 else '') + ', ' + (self.society_ids.city if self.society_ids.city else ''), style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,'P.O Box: ' + (self.society_ids.street2 if self.society_ids.street2 else ''),style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,
                              'Tel: ' + (self.society_ids.phone if self.society_ids.phone else '') + ', ' + 'Fax: ' + (self.society_ids.fax if self.society_ids.fax else '') + ', ' + 'Email: ' + (self.society_ids.email if self.society_ids.email else ''),style_center_align_without_border)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, self.society_ids.website if self.society_ids.website else '',style_center_align_without_border)
            row_no += 3
            sheet.write_merge(row_no, row_no, 0, 10, 'Fee Reconciliation', company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, 'as on :' + time.strftime('%d/%m/%Y'), answer_center)
        if (not self.society_ids and not self.school_ids) or (len(self.school_ids) > 1 and not self.society_ids):
            soc_list = ''
            obj = self.env['res.company'].search([('type', '=', 'society')])
            for record in obj:
                soc_list += str(record.name) + ', '
            sheet.write_merge(row_no, row_no, 0, 10,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,soc_list[:-2],company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,'')
            row_no += 3
            sheet.write_merge(row_no, row_no, 0, 10, 'Fee Reconciliation', company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, 'as on :' + time.strftime('%d/%m/%Y'), answer_center)
        if (len(self.society_ids) > 1) or (len(self.society_ids) > 1 and len(self.school_ids) > 1):
            sc_list = ''
            for record in self.society_ids:
                sc_list += str(record.name) + ', '
            sheet.write_merge(row_no, row_no, 0, 10,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, sc_list[:-2],company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,'')
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10,'')
            row_no += 3
            sheet.write_merge(row_no, row_no, 0, 10, 'Fee Reconciliation', company_address)
            row_no += 1
            sheet.write_merge(row_no, row_no, 0, 10, 'as on :' + time.strftime('%d/%m/%Y'), answer_center)
        
        row_no = 10;
        sheet.row(10).height = 350; 
        row_no += 1
        for data in self.get_data():
            for school in data['school_s']:
                row_no += 2
                sheet.write_merge(row_no, row_no, 0,10, school['school_name'] or '', header)
                row_no += 1
                sheet.col(0).width = 256 * 15
                sheet.write(row_no, 0, 'Class', header)
                
                sheet.col(1).width = 256 * 15
                sheet.write(row_no, 1, 'Student Count', header)
                
                sheet.col(1).width = 256 * 15
                sheet.write(row_no, 2, 'Open. DR', header)
                
                sheet.col(1).width = 256 * 15
                sheet.write(row_no, 3, 'Open. CR', header)
                
                
                sheet.col(1).width = 256 * 15
                sheet.write(row_no, 4, 'Charge', header)
                
                
                sheet.col(1).width = 256 * 15
                sheet.write(row_no, 5, 'Concession', header)
                
                sheet.col(1).width = 256 * 15
                sheet.write(row_no, 6, 'Collection', header)
                        
                sheet.col(2).width = 256 * 17
                sheet.write(row_no, 7, 'Adj. DR', header)        
                sheet.col(3).width = 256 * 17
                sheet.write(row_no, 8, 'Adj. CR', header)        
                sheet.col(4).width = 256 * 17
                sheet.write(row_no, 9, 'Close. DR', header)        
                sheet.col(5).width = 256 * 17
                sheet.write(row_no, 10, 'Close CR', header)
                row_no += 1
                for class_id in school['class_s']:
                    sheet.write(row_no, 0, class_id['class_name'] , answer)
                    sheet.write(row_no, 1, class_id['stu_count'] , answer_center)
                    sheet.write(row_no, 2, class_id['open_dr'] , answer)
                    sheet.write(row_no, 3, class_id['open_cr'] , answer)
                    sheet.write(row_no, 4, class_id['charge'] , answer)
                    sheet.write(row_no, 5, class_id['concession'] , answer)
                    sheet.write(row_no, 6, class_id['collection'] , answer)
                    sheet.write(row_no, 7, class_id['adj_dr'] , answer)
                    sheet.write(row_no, 8, class_id['adj_cr'] , answer)
                    sheet.write(row_no, 9, class_id['close_dr'] , answer) 
                    sheet.write(row_no, 10, class_id['close_cr'] , answer) 
                    row_no += 1
                sheet.write(row_no, 0, 'Total' , header)
                sheet.write(row_no, 1, school['total_stu_count'] , header)
                sheet.write(row_no, 2, school['total_open_dr'] , header_right)
                sheet.write(row_no, 3, school['total_open_cr'] , header_right)
                sheet.write(row_no, 4, school['total_charge'] , header_right)
                sheet.write(row_no, 5, school['total_concession'] , header_right)
                sheet.write(row_no, 6, school['total_collection'] , header_right)
                sheet.write(row_no, 7, school['total_adj_dr'] , header_right)
                sheet.write(row_no, 8, school['total_adj_cr'] , header_right)
                sheet.write(row_no, 9, school['total_close_dr'] , header_right) 
                sheet.write(row_no, 10, school['total_close_cr'] , header_right) 
                row_no += 1
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
        return self.env['report'].get_action(self, 'pappaya_fees.class_wise_feereconciliation_pdf_report')

    @api.multi
    def detail_excel_report(self):
        if not self.get_data():
            raise ValidationError(_("No record found..!"))
        start_date = fields.Date.from_string(self.from_date)
        end_date = fields.Date.from_string(self.to_date)
        if start_date > end_date:
            raise ValidationError(_("To date should not be less than from date."))
        #if not self.get_data():
            # ValidationError(_("No record found..!"))
        data = base64.encodestring(self.from_data())
        attach_vals = {
            'name':'%s.xls' % ('Fee Reconciliation Report'),
            'datas':data,
            'datas_fname':'%s.xls' % ('Fee Reconciliation Report'),
         }
        doc_id = self.env['ir.attachment'].create(attach_vals)
        return {
            'type': 'ir.actions.act_url',
            'url':'web/content/%s?download=true'%(doc_id.id),
            'target': 'self',
        }
    
    
    
    
