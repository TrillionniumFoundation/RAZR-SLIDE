"""Four explicit finite nominal endpoint states; no complete-domain claim."""
ENDPOINTS={
    'stow_tabs_0':{'slide':0.,'descent':0.,'left_tab':0.,'right_tab':0.,'open_hold':False,'open_support':False,'expected_bodies':154},
    'stow_tabs_3':{'slide':0.,'descent':0.,'left_tab':3.,'right_tab':3.,'open_hold':False,'open_support':False,'expected_bodies':154},
    'predock':{'slide':79.75,'descent':0.,'left_tab':3.,'right_tab':3.,'open_hold':False,'open_support':False,'expected_bodies':154},
    'open_installed':{'slide':79.75,'descent':8.2,'left_tab':3.,'right_tab':3.,'open_hold':True,'open_support':True,'expected_bodies':161},
}
REMAINING=('independent left/right manual TAB and slot flank domains',
    'independent KEY and crosshead offsets with true ContactProfile branches',
    'independent telescope allocations and seating domain',
    'all intermediate slide and mixed motion laws including FPC/OLED/SPRING',
    'out-of-profile slot states and actual hard-stop or contact explanation',
    'reverse path, preload, forces, materials, tolerances and assembly/repair path')
