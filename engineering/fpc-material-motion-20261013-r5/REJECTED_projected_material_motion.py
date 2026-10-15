#!/usr/bin/env python3
"""Fixed material-station analysis on unchanged R46/R47/R50 research paths.

Arc length from A identifies material: sigma never means an old sample index.
Frames are conditional reconstructions of the old R50 research profiles, not
supplier-authorized material directors, neutral axes or physical fatigue data.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,math,sys,time
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
TAGS=['A_CONNECTOR_STUB','A_Z_TRANSITION_LEG','ROLLING_U_ARC','B_Z_TRANSITION_LEG','B_CONNECTOR_STUB']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def source_modules(folder=ROOT):
    manifest=json.loads((folder/'frozen_source_manifest.json').read_text())
    for row in manifest['inputs']:
        if sha(folder/row['copy'])!=row['sha256']:raise ValueError('frozen copied input differs: '+row['copy'])
    sys.path.insert(0,str(folder/'frozen_input'))
    r50=load('r50_material_input',folder/'frozen_input/r50_full_span_finite_ribbon.py')
    r50.R47=folder/'frozen_input/R47'
    r47,r,A,B=r50.get_reference()
    return r50,r47,r,A,B

def normalized(v):
    v=np.asarray(v,float);n=np.linalg.norm(v,axis=-1,keepdims=True)
    if np.any(~np.isfinite(n)) or np.any(n<1e-10):raise ValueError('degenerate material frame')
    return v/n

def faithful_R50_frames(points):
    """Same actual section-director rule, independently verified against CQ."""
    frames=[];prior=None
    for i,p in enumerate(points):
        tangent=normalized(points[min(i+1,len(points)-1)]-points[max(i-1,0)])
        if prior is not None:
            w=prior-np.dot(prior,tangent)*tangent
            if np.linalg.norm(w)<1e-5:w=np.cross(tangent,[0,0,1])
        else:w=np.cross(tangent,[0,0,1])
        if np.linalg.norm(w)<1e-5:w=np.cross(tangent,[0,1,0])
        w=normalized(w)
        if prior is not None and np.dot(w,prior)<0:w=-w
        d=normalized(np.cross(tangent,w));prior=w
        frames.append(np.column_stack((w,d,tangent)))
    return np.asarray(frames)

class MaterialCurve:
    def __init__(self,r,c,s,q,target):
        if not all(math.isfinite(x) for x in (s,q,target)) or not 0<=s<=79.75 or not 0<=q<=8.2 or (q>0 and s!=79.75):raise ValueError('pose is outside authorized sequential Y+Z path')
        self.r=r;self.c=c;self.s=s;self.q=q;self.target=target;self.row=r.pose(c,s,q,target)
        self.fold=self.row['fold_y_mm'];self.z=self.row['world_arc_z_mm']
        self.A=np.array([r.R39.X_CONN,r.R39.Y_A,r.R39.Z_A],float)
        self.Aleg=np.array([c.xa(),r.R39.Y_A,r.R39.Z_A],float)
        self.Bleg=np.array([c.xb(),r.R39.Y_B0+s,r.R39.Z_B0+q],float)
        self.B=np.array([r.R39.X_CONN,r.R39.Y_B0+s,r.R39.Z_B0+q],float)
        self.leg_parameters={1:(self.fold-r.R39.Y_A,self.z-r.R39.Z_A),3:(r.R39.Y_B0+s-self.fold,r.R39.Z_B0+q-self.z)}
        a=np.linalg.norm(self.Aleg-self.A);b=np.linalg.norm(self.B-self.Bleg)
        lengths=[a,self.partial_leg(1,np.array([1.]))[0],math.pi*c.radius_mm,self.partial_leg(3,np.array([1.]))[0],b]
        self.bounds=np.r_[0.,np.cumsum(lengths)]
        if abs(self.bounds[-1]-target)>1e-8:raise ValueError('fixed material total length differs from source')

    def partial_leg(self,leg,u):
        u=np.atleast_1d(np.asarray(u,float));dy,dz=self.leg_parameters[leg]
        points=u[:,None]*self.r.R39.QUAD_U[None,:]
        speed=np.sqrt(dy*dy+(dz*6*points*(1-points))**2)
        return u*np.sum(self.r.R39.QUAD_W[None,:]*speed,axis=1)

    def invert_leg(self,leg,distance):
        distance=np.asarray(distance,float);dy,dz=self.leg_parameters[leg]
        full=self.partial_leg(leg,np.array([1.]))[0];u=np.clip(distance/full,0,1)
        for _ in range(8):
            residual=self.partial_leg(leg,u)-distance
            speed=np.sqrt(dy*dy+(dz*6*u*(1-u))**2)
            u=np.clip(u-residual/speed,0,1)
        if len(u) and np.max(np.abs(self.partial_leg(leg,u)-distance))>1e-9:raise ValueError('fixed material arclength inverse did not converge')
        return u

    def source_vertex_stations(self):
        stations=list(np.linspace(self.bounds[0],self.bounds[1],5))
        stations.extend(self.bounds[1]+self.partial_leg(1,np.linspace(0,1,21)[1:]))
        stations.extend(np.linspace(self.bounds[2],self.bounds[3],61)[1:])
        stations.extend(self.bounds[3]+self.partial_leg(3,np.linspace(0,1,21)[1:]))
        stations.extend(np.linspace(self.bounds[4],self.bounds[5],5)[1:])
        result=np.asarray(stations)
        if len(result)!=109 or np.any(np.diff(result)<=0):raise ValueError('old sections do not make a monotone material map')
        return result

    def evaluate(self,sigma):
        sigma=np.atleast_1d(np.asarray(sigma,float))
        if np.any(~np.isfinite(sigma)) or np.any(sigma<-1e-9) or np.any(sigma>self.target+1e-9):raise ValueError('material stations outside original fixed length')
        sigma=np.clip(sigma,0,self.target)
        seg=np.minimum(np.searchsorted(self.bounds,sigma,side='right')-1,4)
        xyz=np.zeros((len(sigma),3));t=np.zeros_like(xyz);k=np.zeros_like(xyz)
        for group in range(5):
            select=np.flatnonzero(seg==group);distance=sigma[select]-self.bounds[group]
            if not len(select):continue
            if group in (0,4):
                a,b=(self.A,self.Aleg) if group==0 else (self.Bleg,self.B)
                xyz[select]=a+distance[:,None]/(self.bounds[group+1]-self.bounds[group])*(b-a);t[select]=normalized(b-a)
            elif group in (1,3):
                u=self.invert_leg(group,distance);dy,dz=self.leg_parameters[group]
                start=self.Aleg if group==1 else np.array([self.c.xb(),self.fold,self.z])
                xyz[select]=start+np.column_stack((np.zeros_like(u),dy*u,dz*(3*u*u-2*u*u*u)))
                first=np.column_stack((np.zeros_like(u),np.full_like(u,dy),dz*6*u*(1-u)))
                second=np.column_stack((np.zeros_like(u),np.zeros_like(u),dz*(6-12*u)))
                tangent=normalized(first);speed2=np.sum(first**2,axis=1)
                t[select]=tangent;k[select]=(second-tangent*np.sum(tangent*second,axis=1)[:,None])/speed2[:,None]
            else:
                theta=distance/self.c.radius_mm
                xyz[select]=np.column_stack((self.c.cx_mm-self.c.radius_mm*np.cos(theta),self.fold+self.c.radius_mm*np.sin(theta),np.full_like(theta,self.z)))
                t[select]=np.column_stack((np.sin(theta),np.cos(theta),np.zeros_like(theta)))
                k[select]=np.column_stack((np.cos(theta),-np.sin(theta),np.zeros_like(theta)))/self.c.radius_mm
        sharp=(np.abs(sigma-self.bounds[1])<1e-8)|(np.abs(sigma-self.bounds[4])<1e-8)
        return xyz,t,k,seg,sharp

def associated_frames(curve,sigma,old_sigma,old_frames):
    xyz,t,k,seg,sharp=curve.evaluate(sigma)
    i=np.clip(np.searchsorted(old_sigma,sigma,side='right')-1,0,107)
    eta=(np.asarray(sigma)-old_sigma[i])/(old_sigma[i+1]-old_sigma[i])
    cad_w=old_frames[i,:,0]*(1-eta[:,None])+old_frames[i+1,:,0]*eta[:,None]
    w=normalized(cad_w-t*np.sum(cad_w*t,axis=1)[:,None]);d=normalized(np.cross(t,w))
    frame=np.stack((w,d,t),axis=2)
    return frame,(xyz,t,k,seg,sharp),i,eta

def local_kinematics(curve,sigma,old_sigma,old_frames,h=.025):
    f,geometry,i,eta=associated_frames(curve,sigma,old_sigma,old_frames)
    xyz,t,k,seg,sharp=geometry
    lower=np.maximum(0,np.asarray(sigma)-h);upper=np.minimum(curve.target,np.asarray(sigma)+h)
    fm,*_=associated_frames(curve,lower,old_sigma,old_frames)
    fp,*_=associated_frames(curve,upper,old_sigma,old_frames)
    relative=np.einsum('nji,njk->nik',fm,fp)
    rotation=Rotation.from_matrix(relative).as_rotvec()
    world_angular_rate=np.einsum('nij,nj->ni',fm,rotation)/(upper-lower)[:,None]
    twist=np.sum(world_angular_rate*t,axis=1)
    invalid=sharp|(np.abs(np.asarray(sigma)-curve.bounds[1])<=h)|(np.abs(np.asarray(sigma)-curve.bounds[4])<=h)
    twist[invalid]=np.nan
    curvatures=np.column_stack((np.sum(k*f[:,:,0],axis=1),np.sum(k*f[:,:,1],axis=1)))
    curvatures[sharp]=np.nan
    return {'xyz':xyz,'frames':f,'curvatures':curvatures,'twist':twist,'segment':seg,'sharp':sharp,'cell':i,'eta':eta}

def verify_native_cells(r50,r47,r,A,B,c,target,sigma,outfolder):
    """Check mapped centers and interior corners in actual unaltered ruled cells."""
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.TopAbs import TopAbs_IN
    from OCP.gp import gp_Pnt
    from occ_signed_volume import validated_solid_volume,common
    rows=[];outfolder.mkdir(parents=True,exist_ok=True)
    for name,s,q in [('SLIDE_20p125',20.125,0.),('DOCK_2p013',79.75,2.013),('OPEN_SEATED',79.75,8.2)]:
        curve=MaterialCurve(r,c,s,q,target);old_pts,_,_,_=r47.full_centerline(r,c,s,q,target)
        old_sigma=curve.source_vertex_stations();frames=faithful_R50_frames(old_pts)
        wires,normals,tangents,_=r50.sections(old_pts)
        imported=np.array([np.column_stack((w,d,t)) for (w,d),t in zip(normals,tangents)])
        frame_delta=float(np.max(np.abs(imported-frames)))
        if frame_delta>1e-12:raise ValueError('own directors differ from actual R50 CQ section code')
        cells=r50.solid_cells(wires)
        for cell in cells:validated_solid_volume(cell)
        index=np.clip(np.searchsorted(old_sigma,sigma,side='right')-1,0,107)
        eta=(sigma-old_sigma[index])/(old_sigma[index+1]-old_sigma[index])
        centers=old_pts[index]*(1-eta[:,None])+old_pts[index+1]*eta[:,None]
        cad_w=frames[index,:,0]*(1-eta[:,None])+frames[index+1,:,0]*eta[:,None]
        cad_d=frames[index,:,1]*(1-eta[:,None])+frames[index+1,:,1]*eta[:,None]
        classifiers={i:BRepClass3d_SolidClassifier(cells[i].wrapped) for i in set(index)}
        checked=0
        for n,idx in enumerate(index):
            for dw,dt in [(0,0),(-.49,-.49),(.49,-.49),(.49,.49),(-.49,.49)]:
                p=centers[n]+dw*r50.WIDTH*cad_w[n]+dt*r50.THICKNESS*cad_d[n]
                classifier=classifiers[idx];classifier.Perform(gp_Pnt(*map(float,p)),1e-6)
                if classifier.State()!=TopAbs_IN and not classifier.IsOnAFace():raise ValueError(f'R50 ruled cell station containment failed {name} sigma={sigma[n]} cell={idx}')
                checked+=1
        actual=curve.evaluate(sigma)[0];deviation=np.linalg.norm(actual-centers,axis=1)
        bw=B.translate((0,s,q-8.2));validated_solid_volume(A);validated_solid_volume(bw)
        witnesses=[]
        for body,body_name in [(A,'A'),(bw,'B')]:
            classifier=BRepClass3d_SolidClassifier(body.wrapped)
            for n,p in enumerate(centers):
                if sigma[n]<6 or sigma[n]>target-6:continue
                classifier.Perform(gp_Pnt(*map(float,p)),1e-6)
                if classifier.State()==TopAbs_IN:
                    sphere=r50.cq.Solid.makeSphere(.02,r50.cq.Vector(*map(float,p)))
                    volume=common(sphere,body)['checked_volume_mm3']
                    if volume<=1e-7:raise ValueError('negative collision witness lost positive guarded volume')
                    witnesses.append({'body':body_name,'fixed_material_sigma_mm':float(sigma[n]),'actual_R50_cell':int(index[n]),'center_xyz_mm':list(map(float,p)),'sphere_radius_mm':.02,'guarded_actual_positive_common_mm3':volume});break
        file=outfolder/(name+'_UNMODIFIED_R50_RESEARCH_PROXY.step')
        r50.cq.exporters.export(r50.cq.Compound.makeCompound([A,bw,*cells]),str(file),exportType='STEP')
        loaded=r50.cq.importers.importStep(str(file)).val()
        leaves=loaded.Solids()
        if len(leaves)!=110:raise ValueError('exported research assembly lost solid payload')
        for leaf in leaves:validated_solid_volume(leaf)
        rows.append({'pose':name,'slide_mm':s,'normal_mm':q,'actual_CQ_loft_cells':108,'material_section_point_queries':checked,'full_payload_and_positive_solid_guard_applied':True,'director_max_abs_delta_from_actual_CQ_section_source':frame_delta,'analytic_curve_to_old_chord_max_mm':float(np.max(deviation)),'remaining_body_collision_witnesses':witnesses,'STEP_filename':file.name,'STEP_sha256':sha(file),'reimported_positive_solid_leaves':len(leaves),'manufacturing_go':False})
        print('actual native cells',name,checked,'mapped points',len(witnesses),'positive body witnesses',flush=True)
    return rows

def motion_scan(r50,r47,r,c,target,sigma):
    states=r.R39.all_path_states();history={k:[] for k in ['xyz','frames','curvatures','twist','segment','source_vertex_sigma']}
    max_roundtrip=0.;max_length=0.;b_roll=[];b0=None;fixed_index_arc_entry=[]
    for number,(s,q) in enumerate(states):
        curve=MaterialCurve(r,c,s,q,target);pts,_,_,_=r47.full_centerline(r,c,s,q,target)
        old_sigma=curve.source_vertex_stations();frames=faithful_R50_frames(pts)
        vertices=curve.evaluate(old_sigma)[0];delta=float(np.max(np.linalg.norm(vertices-pts,axis=1)))
        if delta>1e-8:raise ValueError('fixed arclength model changed original geometric vertices')
        max_roundtrip=max(max_roundtrip,delta);max_length=max(max_length,abs(curve.bounds[-1]-target))
        sample=local_kinematics(curve,sigma,old_sigma,frames)
        for k in ('xyz','frames','curvatures','twist','segment'):history[k].append(sample[k])
        history['source_vertex_sigma'].append(old_sigma)
        fw=sample['frames'][-1,:,0];ft=sample['frames'][-1,:,2]
        if b0 is None:b0=fw.copy()
        b_roll.append(math.atan2(float(np.dot(ft,np.cross(b0,fw))),float(np.dot(b0,fw))))
        fixed_index_arc_entry.append(float(old_sigma[24]))
        if number%80==0:print('material motion pose',number+1,'of',len(states),'q',q,flush=True)
    data={k:np.asarray(v) for k,v in history.items()};data['states']=np.asarray(states);data['sigma']=sigma;data['B_proxy_endpoint_roll_rad']=np.asarray(b_roll)
    f=data['frames'];orth=np.einsum('...ji,...jk->...ik',f,f)
    max_orth=float(np.max(np.abs(orth-np.eye(3))));det_error=float(np.max(np.abs(np.linalg.det(f)-1)))
    changes=Rotation.from_matrix(np.einsum('...ji,...jk->...ik',f[:-1],f[1:])).magnitude()
    return data,{'state_count':len(states),'fixed_material_station_count':len(sigma),'total_station_poses':len(states)*len(sigma),'Y_slide_states_including_PREDOCK':321,'normal_seating_states_excluding_duplicate_PREDOCK':160,
      'max_source_vertex_arclength_roundtrip_position_error_mm':max_roundtrip,'max_fixed_material_total_length_error_mm':max_length,'max_frame_orthonormal_error':max_orth,'max_frame_determinant_error':det_error,
      'old_node_24_material_sigma_range_mm':[min(fixed_index_arc_entry),max(fixed_index_arc_entry)],'old_node_24_material_slip_mm':max(fixed_index_arc_entry)-min(fixed_index_arc_entry),
      'proxy_B_endpoint_required_roll_range_deg':list(map(float,np.rad2deg([min(b_roll),max(b_roll)]))),'proxy_B_endpoint_roll_is_actual_clamp_permission':False,
      'max_adjacent_motion_sample_material_frame_change_deg':float(np.rad2deg(np.max(changes))),
      'max_abs_width_axis_curvature_per_mm':float(np.nanmax(np.abs(data['curvatures'][...,0]))),'max_abs_thickness_axis_curvature_per_mm':float(np.nanmax(np.abs(data['curvatures'][...,1]))),
      'max_abs_R50_associated_material_twist_rad_per_mm':float(np.nanmax(np.abs(data['twist']))),'spatial_twist_stencil_halfspan_mm':.025,
      'sharp_zero_radius_A_and_B_material_stations_mm':[float(np.linalg.norm(np.array([c.xa(),r.R39.Y_A,r.R39.Z_A])-np.array([r.R39.X_CONN,r.R39.Y_A,r.R39.Z_A]))),target-abs(c.xb()-r.R39.X_CONN)],
      'sharp_joint_actual_bend_radius_mm':0,'source_frame_interpolation_is_not_elastic_equilibrium':True,'continuous_motion_clearance_or_material_strain_certificate':False,'actual_material_neutral_axis_and_copper_strain':None,'manufacturing_go':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--out-dir',type=Path,required=True);p.add_argument('--no-cad',action='store_true');a=p.parse_args();out=a.out_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    r50,r47,r,A,B=source_modules();c=r.CANDIDATES[2];target=r.target_length(c)
    sigma=np.unique(np.r_[np.linspace(0,target,321),abs(c.xa()-r.R39.X_CONN),target-abs(c.xb()-r.R39.X_CONN)])
    before={row['copy']:sha(ROOT/row['copy']) for row in json.loads((ROOT/'frozen_source_manifest.json').read_text())['inputs']}
    data,summary=motion_scan(r50,r47,r,c,target,sigma)
    np.savez_compressed(out/'material_history.npz',**data)
    native=[] if a.no_cad else verify_native_cells(r50,r47,r,A,B,c,target,sigma,out/'cad')
    after={row:sha(ROOT/row) for row in before}
    if before!=after:raise ValueError('frozen source input changed')
    report={'candidate':c.name,'candidate_fixed_analytic_total_length_mm':target,'research_width_mm':r50.WIDTH,'research_total_thickness_mm':r50.THICKNESS,'summary':summary,'actual_native_CAD_material_alignment':native,'source_hashes_before':before,'source_hashes_after':after,'source_bytes_unchanged':before==after,'history_shapes':{k:list(v.shape) for k,v in data.items()},'histories_are_analytic_conditional_research_not_real_copper_stress':True,'manufacturing_go':False}
    (out/'motion_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
