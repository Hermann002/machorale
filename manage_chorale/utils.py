def add_materials_event_for_html(event):
    if event.event_type.startswith("contribution"):
        event.material = "payment"
        return event
    
