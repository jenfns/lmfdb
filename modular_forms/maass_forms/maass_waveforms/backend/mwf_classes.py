from modular_forms.backend.mf_classes import MFDataTable
from mwf_utils import *
import bson

class MaassFormTable(MFDataTable):
    r"""
    To Display one form
    """
    def __init__(self,dbname='',**kwds):
        MFDataTable.__init__(self,dbname,**kwds)    
        self._id = kwds.get('id',None)
        if not self._id:
            mwf_logger.critical("You must supply an id!")

            
    def set_table(self,**kwds):
        self._name = kwds.get('name','')
        self._table=dict()
        self._table=[]
        self._is_set=True
        for r in range(self._nrows):
            self._table.append([])
            for k in range(self._ncols):
                self._table[r].append({})
                rec_len = self._ncols*self._nrows
        skip = rec_len*self._skip_rec
        mwf_logger.debug("rows: {0}".format(self._nrows))
        mwf_logger.debug("cols: {0}".format(self._ncols))
        mwf_logger.debug("In mwf.set_table: collections : {0}".format(self.collection()))
        mwf_logger.debug("skip: {0} rec_len:{1}".format(skip,rec_len))
        # only have one collection here...
        c = self.collection()[0]
        mwf_logger.debug("collection: {0}".format(c))
        limit = self._nrows
        skip = self._skip_rec
        mwf_logger.debug("limit: {0}, skip: {1}".format(limit,skip))
        f=c.find_one({'_id':bson.objectid.ObjectId(self._id)}) #.skip(skip).limit(limit)
        if not f:
            mwf_logger.critical("You did not supply a valid id! Got:{0}".format(self._id))
            return 
        self._props['Eigenvalue'] = f['Eigenvalue']
        self._props['Symmetry'] = f['Symmetry']
        self._props['Weight'] = f['Weight']
        
        try:
            self._props['Character'] = f['Character']
        except:  # Trivial charcter default
            self._props['Character'] = 0
            
        self._props['Level'] = f['Level']        
        #self._props['prec'] = f['prec']
        metadata=dict()
        MD = self._db['metadata']
        mwf_logger.debug("metadata: {0}".format(MD))
        mdfind = MD.find_one({'c_name':self._collection_name})
        mwf_logger.debug("mdfind: {0}".format(mdfind))
        for x in mdfind:
            metadata[x]=mdfind[x]
        self._props['metadata']=metadata
        numc = len(f['Coefficient'])
        mwf_logger.debug("numc: {0}".format(numc))
        self._props['numc']=numc
        if numc == 0:
            self._table=[]
            return
        limit = min(numc,self._nrows)
        self._row_heads=range(limit)
        self._col_heads=['n','C(n)']
        row_min = self._nrows*skip
        mwf_logger.debug("numc: {0}".format(numc))
        self._table=[]
        for n in range(limit):
            self._table.append([0])
        for n in range(limit):
            self._row_heads[n]=n+row_min+1 # one is fbeacuse we have a cusp form
            c = f['Coefficient'][n+row_min]
            self._table[n][0]={'value':c}
            self._table.append(list())



class WebMaassForm(object):
    def __init__(self,db,maassid,**kwds):
        r"""
        Setup a Maass form from maassid in the database db
        of the type MaassDB.
        OPTIONAL parameters:
        - dirichlet_c_only = 0 or 1
        -fnr = get the Dirichlet series coefficients of this function in self only
        - get_coeffs = False if we do not compute or fetch coefficients
        """
        self._db=db
        self.R=None; self.symmetry=-1
        self.weight=0; self.character=0; self.level=1
        self.table={}; self.coeffs={}
        if not isinstance(maassid,(bson.objectid.ObjectId,str)):
            ids=db.find_Maass_form_id(id=maassid)
            if len(ids)==0:
                return
            mwf_logger.debug("maassid is not an objectid! {0}".format(maassid))
            maassid=ids[0]
        self._maassid=bson.objectid.ObjectId(maassid)
        mwf_logger.debug("_id={0}".format(self._maassid))
        ff=db.get_Maass_forms(id=self._maassid)
        #print "ff=",ff
        if len(ff)==0:
            return
        f=ff[0]


        #print "f here=",f
        self.dim = f.get('Dim',1)
        if self.dim==0:
            self.dim=1
        
        self.R=f.get('Eigenvalue',None)
        self.symmetry=f.get('Symmetry',-1)
        self.weight=f.get('Weight',0)
        self.character=f.get('Character',0)
        self.cusp_evs=f.get('Cusp_evs',[])
        self.error=f.get('Error',[])
        self.level=f.get('Level',None)
        self.num_coeff=f.get('Numc',0)
        if self.R ==None or self.level==None:
            return
        ## As default we assume we just have c(0)=1 and c(1)=1 
        self._get_dirichlet_c_only=kwds.get('get_dirichlet_c_only',False)
        self._num_coeff0=kwds.get('num_coeffs',self.num_coeff)
        self._get_coeffs=kwds.get('get_coeffs',True)
        self._fnr=kwds.get('fnr',0)
        if self._get_coeffs:
            self.coeffs=f.get('Coefficient',[0,1,0,0,0])
            if self.coeffs<>[0,1,0,0,0]:
                if self._get_dirichlet_c_only:
                    if len(self.coeffs)==1:
                        self.coeffs=self.coeffs[0]
                else:
                    self.coeffs={}
        else:
            self.coeffs={}
        coeff_id=f.get('coeff_id',None)
        nc = Gamma0(self.level).ncusps()
        self.M0=f.get('M0',nc)
        mwf_logger.debug("coeffid={0}, get_coeffs={1}".format(coeff_id,self._get_coeffs))
        if coeff_id and self._get_coeffs: #self.coeffs==[] and coeff_id:
            ## Let's see if we have coefficients stored
            C = self._db.get_coefficients({"_id":self._maassid})
            if len(C)>=1:
                C=C[0]
                if self._get_dirichlet_c_only:
                    print "setting Dirichlet C!"
                    if self._fnr>len(C):
                        self._fnr=0
                    if self._num_coeff0>len(C[self._fnr][0])-1:
                        self._num_coeff0=len(C[self._fnr][0])-1
                    self.coeffs=[]
                    for j in range(1,self._num_coeff0+1):
                        self.coeffs.append(C[self._fnr][0][j])
                else:
                    print "setting C!"
                    self.coeffs=C
         ## Make sure that self.coeffs is only the current coefficients
        if self._get_coeffs and isinstance(self.coeffs,dict):
            n1=len(self.coeffs.keys())
            mwf_logger.debug("|coeff.keys()|:{0}".format(n1))
            if n1<>self.dim:
                mwf_logger.warning("Got coefficient dict of wrong format!:dim={0} and len(c.keys())={1}".format(self.dim,n1))
            if n1>0:
                for j in range(self.dim):                    
                    n2=len(self.coeffs.get(j,{}).keys())
                    mwf_logger.debug("|coeff[{0}].keys()|:{1}".format(j,n2))
                    if n2<>nc:
                        mwf_logger.warning("Got coefficient dict of wrong format!:num cusps={0} and len(c[0].keys())=".format(nc,n2))
                
        self.nc = 1 #len(self.coeffs.keys())
        if not self._get_dirichlet_c_only:
            pass #self.set_table()
        else:
            self.table={}

    def C(self,r,n,i=0):
        r"""
        Get coeff nr. n at cusp nr. r of self
        """
        if not self.coeffs:
            return None
        raise NotImplementedError
        
        
        
    def the_character(self,conrey=True):
        if not conrey:
            if self.character==0:
                return "trivial"
            else:
                return self.character
        else:
            chi = self._db.getDircharConrey(self.level,self.character)
            #return "\chi_{" + str(self.level) + "}(" +strIO(chi) + ",\cdot)"

         
        
        
    def the_weight(self):
        if self.weight==0:
            return "0"
        else:
            return self.weight
    def fricke(self):
        if len(self.cusp_evs)>1:
            return self.cusp_evs[1]
        else:
            return "undefined"
    def even_odd(self):
        if self.symmetry==1:
            return "odd"
        elif self.symmetry==0:
            return "even"
        else:
            return "undefined"
        
    def set_table(self,fnr=0,cusp=0):
        r"""
        Setup a table with coefficients for function nr. fnr in self,
        at cusp nr. cusp
        """
        table={'nrows':self.num_coeff,
               'ncols':self.dim+1}
        table['data']=[]
        table['negc']=0
        realnumc=0
        if self.num_coeff==0:
            self.table=table
            return
        if self.symmetry<>-1:
            for n in range(self.num_coeff):
                row=[n]
                for k in range(table['ncols']):
                    if self.dim==1:
                        c=None
                        try:
                            c = self.coeffs[fnr][cusp].get(n,None)
                        except KeyError,IndexError:
                            mwf_logger.critical("GOt coefficient in wrong format for id={0}".format(self._maassid))
                        if c<>None:
                            c=CC(c)
                            realnumc+=1
                        row.append(c)
                    else:                        
                        for j in range(self.dim):
                            c = ((self.coeffs.get(j,{})).get(0,None)).get(n,None)
                            if c<>None:
                                #mwf_logger.debug("c={0}".format(c))
                                c1=CC(c)
                                realnumc+=1
                                row.append(c1)
                table['data'].append(row)                #mwf_logger.debug("row={0}".format(row))
        else:
            table['negc']=1
            # in this case we need to have coeffs as dict.
            if not isinstance(self.coeffs,dict):
                self.table={}
                return
            for n in range(len(self.coeffs.keys()/2)):
                row=[n]
                if self.dim==1:
                    for k in range(table['ncols']):
                        cp = self.coeffs.get(n,0)
                        cn = self.coeffs.get(-n,0)
                        row.append((cp,cn))
                        realnumc+=1
                else:
                    for j in range(self.dim):
                        c = (self.coeffs.get(j,{})).get(n,None)
                        if c<>None:
                            c1 = c.get(n,None)
                            cn1 = c.get(-n,None)
                            c1=CC(c1)
                            cn1=CC(cn1)
                            row.append((c1,cn1))
                            realnumc+=1
                        table['data'].append(row)
        self.table=table
        mwf_logger.debug("realnumc={0}".format(realnumc))
