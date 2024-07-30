import frappe
from frappe.utils import flt

@frappe.whitelist()
def make_stock_entry(work_order_id, purpose, qty=None):
    work_order = frappe.get_doc("Work Order", work_order_id)
    wip_warehouse = frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group") and None or work_order.wip_warehouse

    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.update({
        "purpose": purpose,
        "work_order": work_order_id,
        "company": work_order.company,
        "from_bom": 1,
        "bom_no": work_order.bom_no,
        "use_multi_level_bom": work_order.use_multi_level_bom,
        "fg_completed_qty": qty or (flt(work_order.qty) - flt(work_order.produced_qty)),
        "inspection_required": frappe.db.get_value('BOM', work_order.bom_no, 'inspection_required') if work_order.bom_no else 0
    })

    if purpose == "Material Transfer for Manufacture":
        stock_entry.to_warehouse = wip_warehouse
        stock_entry.project = work_order.project
    else:
        stock_entry.from_warehouse = wip_warehouse
        stock_entry.to_warehouse = work_order.fg_warehouse
        stock_entry.project = work_order.project

    stock_entry.set_stock_entry_type()

    for d in work_order.required_items:
        uom = frappe.db.get_value("BOM Explosion Item", {"item_code": d.item_code, "parent": work_order.bom_no}, "stock_uom")
        stock_entry.append("items", {
            "item_code": d.item_code,
            "s_warehouse": d.source_warehouse,
            "t_warehouse": wip_warehouse,
            "qty": flt(d.required_qty) - flt(d.transferred_qty),
            "uom": uom,
            "stock_uom": uom,
        })

    stock_entry.insert()
    
    return stock_entry.as_dict()


@frappe.whitelist()
def update_work_order_items(doc, method):
    if doc.purpose == "Material Transfer for Manufacture":
      
        work_order = frappe.get_doc("Work Order", doc.work_order)
        extra_material_qty = 0

        
        for item in doc.items:
            extra_material_qty += item.qty

        
        for item in work_order.required_items:
            
            extra_qty = next((d.qty for d in doc.items if d.item_code == item.item_code), 0)
            
            
            item.db_set('custom_extra_materials', flt(item.custom_extra_materials) + extra_qty)
            item.db_set('custom_total_qty', flt(item.required_qty) + extra_qty)

       
        work_order.db_set('material_transferred_for_manufacturing', flt(work_order.material_transferred_for_manufacturing) + extra_material_qty)
        work_order.save()



