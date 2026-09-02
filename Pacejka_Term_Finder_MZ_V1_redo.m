% Pacejka_Term_Finder_MZ_V1_redo
% Based on MF-Tire 6.1 (instead of 6.1.2)

function [MZ_ParameterList, mzfit, Alpha] = Pacejka_Term_Finder_MZ_V1_redo(Round, Run, Tire, Fz_nom)
%% Test Information
TestID = strcat('R',string(Round),'_Rn',string(Run));
Type = 'Fy';
TireMan = 'Hoosier';

% Parameter Values
P = 12;
Fz_vals = Fz_nom; %[50 100 150 200 250]
gamma_vals = 2;
 
%% FY Test Information
FYFileName = strcat('FY_Parameters','_',Tire,'_',string(Round),'_',string(Run),'_',string(Fz_nom),'FZ','.mat');

%% Fit Options
opts = optimset('TolFun',1e-8,'MaxFunEvals',120000,'MaxIter',120000,'TolX',1e-8); 
addpath(genpath('FY Data'))
[SplineData] = Raw_Data_Fitter_Mz_V2(Round,Run,Tire);

%% Fit Data Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Ro = 9*0.0254;
Fz   =  Fz_nom .*4.448; %(N)
p_i   = 12*82.737;  %(kPa)
gamma = gamma_vals*pi./180; %(rad)

%% Conversions %%%%
Deg2Rad = pi./180;
ftlbs_2_Nm = 0.3048*4.448;
%% Base Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
V = 25*1.609/3.6;
Fz_0 = Fz;
pio = 12*82.737;  %(kPa)
rl = 8.67*0.0254; %(m)
alpha_str = strcat('SplineData.P12.SA0.IA0.SA_',TestID, '_', string(Fz_nom), 'FZ_12P_0IA');
Alpha = eval(alpha_str).*Deg2Rad; % sa in rad

Vsx = 0;
Vox = V;

%% User Scaling Factors
Lam.Cx = 1;
Lam.mu_x = 1;
Lam.mu_x_star = Lam.mu_x.*(1+Vsx/Vox);
Lam.Ex =  1;
Lam.Fz_0 = 1;
Lam.Kxk =1;
Lam.mu_x_prime = 1;
Lam.Hx = 1;
Lam.Vx = 1;

%% Constants %%
Fz_0_prime = Lam.Fz_0.*Fz_0;
dpi = (p_i-pio)./pio;
dfz = (Fz-Fz_0_prime)./Fz_0_prime;
 
Vcx = 25*0.447;
V  = Vcx./cos(Alpha);
Cos_alph_p = Vcx./(V+0.1);
Alpha_star = Alpha;
gamma_star = sin(gamma);

%% Initial Fit Parameters (Pstat = [isBase, is*dFz, is*Ia, is*dPi is*dFz*dIA])
% Pure Lateral Slip Terms
     q0.Hz1 = 1;   qstat.Hz1  = [1 0 0 0 0];
     q0.Hz2 = 1;   qstat.Hz2  = [0 1 0 0 0];
     q0.Hz3 = 1;   qstat.Hz3  = [0 0 1 0 0];
     q0.Hz4 = 1;   qstat.Hz4  = [0 0 0 0 1];
     
     q0.Bz1 = 1;   qstat.Bz1  = [1 0 0 0 0];
     q0.Bz2 = 1;   qstat.Bz2  = [0 1 0 0 0];
     q0.Bz3 = 1;   qstat.Bz3  = [0 1 0 0 0];
     q0.Bz4 = 1;   qstat.Bz4  = [1 0 0 0 0];
     q0.Bz5 = 1;   qstat.Bz5  = [0 0 1 0 0];
    
     q0.Bz9 = 1;   qstat.Bz9  = [1 0 0 0 0];
     q0.Bz1o = 1;  qstat.Bz1o = [1 0 0 0 0];
     
     q0.Cz1  = 1;  qstat.Cz1  = [1 0 0 0 0]; 
     
     q0.Dz1  = 1;  qstat.Dz1  = [1 0 0 0 0];
     q0.Dz2  = 1;  qstat.Dz2  = [0 1 0 0 0];
     q0.Dz3  = 1;  qstat.Dz3  = [0 0 1 0 0];
     q0.Dz4  = 3;  qstat.Dz4  = [0 0 1 0 0];
     q0.Dz6  = 1;  qstat.Dz6  = [1 0 0 0 0];
     q0.Dz7  = 10;  qstat.Dz7 = [0 1 0 0 0];
     q0.Dz8  = 1;  qstat.Dz8  = [0 0 1 0 0];
     q0.Dz9  = 1;  qstat.Dz9  = [0 0 0 0 1];
     q0.Dz10 = 1;  qstat.Dz10 = [0 0 1 0 0];
     q0.Dz11 = 3;  qstat.Dz11 = [0 0 0 0 1];
     
     q0.Ez1  = 1;  qstat.Ez1  = [1 0 0 0 0];
     q0.Ez2  = 1;  qstat.Ez2  = [0 1 0 0 0];
     q0.Ez3  = 1;  qstat.Ez3  = [0 1 0 0 0];
     q0.Ez4  = 1;  qstat.Ez4  = [1 0 0 0 0];
     q0.Ez5  = 1;  qstat.Ez5  = [0 0 1 0 0];
     
     
     
    epsilon.y = 0.1;
    epsilon.k = 0.1;
    Zeta.z2 = 1;       
    Zeta.z3 = 1;
%% Parameter Lists
 
Ques     =  [repelem({'q0.'},length(fieldnames(q0)),1), fieldnames(q0)];
%Arrs     =  [repelem({'r0.'},length(fieldnames(r0)),1), fieldnames(r0)];
MZ_ParameterList = [Ques];%; Arrs];
x0 = zeros(length(MZ_ParameterList),1);

for n = 1:length(MZ_ParameterList) 
    var = strcat( MZ_ParameterList{n,1}, MZ_ParameterList{n,2} );
    x0(n,1) = eval(var);
end


%% Output Figure Creation 
% Pure Slip Output Figure %% 
OutFig.Fig.Pure = figure(1);
clf(OutFig.Fig.Pure)
OutFig.Fig.Pure.Name = 'Pure Slip Fitting Results';

OutFig.TabGroup.Pure= uitabgroup(OutFig.Fig.Pure);

% Combined Slip Output Figure %
% OutFig.Fig.Comb = figure(2);
% clf(OutFig.Fig.Comb )
% OutFig.Fig.Comb.Name = 'Combined Slip Fitting Results';
% OutFig.TabGroup.Comb = uitabgroup(OutFig.Fig.Comb);
%  

%% Base Constants For Nominal Load and Zero Inlincation Angle (Negates all terms multiplied by dFz, gamma(IA), or dPi)
m = 0;
q = 0;
j = 0;
k = 0;
r = 0;
s = 0;
t = 0;
p = 0;

for n = 1:length(MZ_ParameterList)
    var = MZ_ParameterList{n,2};
    if contains(MZ_ParameterList{n,1},'q0.') == 1
        if qstat.(var)(1) == 1
            m = m +1;
            BaseList{m,1} = 'q.';
            BaseList{m,2} = var;
            BaseList{m,3} = x0(n,1);
            x0b(m,1) = x0(n,1);

        elseif qstat.(var)(2) == 1
             q = q +1;
            FzList{q,1} = 'q.';
            FzList{q,2} = var;
            FzList{q,3} = x0(n,1);
            x0fz(q,1) = x0(n,1);

        elseif qstat.(var)(3) == 1
             j = j +1;
            IAList{j,1} = 'q.';
            IAList{j,2} = var;
            IAList{j,3} = x0(n,1);
            x0IA(j,1) = x0(n,1);
            
        elseif qstat.(var)(4) ==1
            p = p+1;
            dPiList{p,1} = 'q.';
            dPiList{p,2} = var;
            dPiList{p,3} = x0(n,1);
            x0dPi(p,1) = x0(n,1);
            
        elseif qstat.(var)(5) ==1
            k = k+1;
            IAdFzList{k,1} = 'q.';
            IAdFzList{k,2} = var;
            IAdFzList{k,3} = x0(n,1);
            x0IAFz(k,1) = x0(n,1);
        end
        
% %     elseif contains(ParameterList{n,1},'r0.') == 1
% %         if Rstat.(var)(1) == 1
% %             r = r +1;
% %             CombBaseList{r,1} = 'r.';
% %             CombBaseList{r,2} = var;
% %             CombBaseList{r,3} = x0(n,1);
% %             xc0b(r,1) = x0(n,1);
% %         elseif Rstat.(var)(2) == 1
% %              s = s +1;
% %             CombFzList{s,1} = 'r.';
% %             CombFzList{s,2} = var;
% %             CombFzList{s,3} = x0(n,1);
% %             xc0fz(s,1) = x0(n,1);
% %         elseif Rstat.(var)(3) == 1
% %              t = t +1;
% %             CombIAList{t,1} = 'r.';
% %             CombIAList{t,2} = var;
% %             CombIAList{t,3} = x0(n,1);
% %             xc0IA(t,1) = x0(n,1);
% %         end
    end
            
end
 
%% Base Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
Fz  = Fz_0_prime;
dfz = 0;
[K_yalpha,Cy,mu_y,Dy,By,K_ygo,S_Hy,S_Vy,K_yalphag0,Fy_og0] = ParameterLoad(FYFileName,Fz_0_prime,0,Alpha_star,Fz,dfz);
 
ubb = [0.01,  70, 20,  5.0,  0,  20,  20,  20, 15,  20]';
lbb = [-0.01, -20,20,  -5.0, -20, 0, -20, -20 , -20, -20]';

BaseFit.K_yalpha_p = K_yalpha + epsilon.k;

BaseFit.S_Hf     = S_Hy + S_Vy./BaseFit.K_yalpha_p;
BaseFit.S_Ht     = @(Xb) Xb(1);
BaseFit.alpha_t  = @(Xb) Alpha_star + BaseFit.S_Ht(Xb);
BaseFit.alpha_r  = @(Xb)  Alpha_star + BaseFit.S_Hf;
BaseFit.Bt       = @(Xb) Xb(2).*(1+Xb(3));
BaseFit.Ct       = @(Xb) Xb(6);
BaseFit.Dto      = @(Xb) Fz.*(Ro./Fz_0_prime).*(Xb(7));
BaseFit.Dt       = @(Xb) BaseFit.Dto(Xb).*(1);
BaseFit.Et       = @(Xb) Xb(9).*(1 +(Xb(10)).*(2/pi).*atan(BaseFit.Bt(Xb).*BaseFit.Ct(Xb).*BaseFit.alpha_t(Xb)))  ;
BaseFit.Br       = @(Xb) (Xb(4) + Xb(5).*Cy.*By);
BaseFit.Cr       = 1;
BaseFit.Dr       = @(Xb) Fz.*Ro.*(Xb(8))*Cos_alph_p;
% BaseFit.Kzao     = @(Xb) BaseFit.Dto(Xb).*K_yalphag0;
% BaseFit.Kzgo     = @(Xb) Fz.*Ro(Xb(9)- BaseFit.Dto(Xb).*K_ygo); 
BaseFit.to       = @(Xb) BaseFit.Dt(Xb).*cos( BaseFit.Ct(Xb).*atan(BaseFit.Bt(Xb).*BaseFit.alpha_t(Xb)-BaseFit.Et(Xb).*(BaseFit.Bt(Xb).*BaseFit.alpha_t(Xb)- atan(BaseFit.Bt(Xb).*BaseFit.alpha_t(Xb))))).*Cos_alph_p;
BaseFit.Mzo_p    = @(Xb) -BaseFit.to(Xb).*Fy_og0;
BaseFit.Mzro     = @(Xb) BaseFit.Dr(Xb).*cos(BaseFit.Cr.*atan(BaseFit.Br(Xb).*BaseFit.alpha_t(Xb))).*Cos_alph_p;
BaseFit.Mzo      = @(Xb,Alpha_star) BaseFit.Mzo_p(Xb) + BaseFit.Mzro(Xb); 

MzVar = strcat('MZ_',TestID,'_',string(Fz_nom),'FZ_12P_0IA');
ydata =SplineData.P12.SA0.IA0.(MzVar).*ftlbs_2_Nm; % converting MZ data to Nm

opts_base = optimset('TolFun',1e-8,'MaxFunEvals',400000 ,'MaxIter',400000 ,'TolX',1e-8,'FinDiffType','central'); 
Xb = lsqcurvefit(BaseFit.Mzo,x0b,Alpha_star,ydata,lbb,ubb,opts_base);

 
mzfit.Base =feval(BaseFit.Mzo ,Xb,Alpha_star);

% Check.Base.S_Hy = feval(BaseFit.S_Hy,Xb);
% Check.Base.mu_y = feval(BaseFit.mu_y,Xb);
% Check.Base.C_y = feval(BaseFit.C_y,Xb);
% Check.Base.D_y = feval(BaseFit.D_y,Xb);
 Check.Base.ET = feval(BaseFit.Et,Xb);
% Check.Base.Ky_a = feval(BaseFit.Ky_a,Xb);
% Check.Base.B_y = feval(BaseFit.B_y,Xb);
% Check.Base.S_Vy = feval(BaseFit.S_Vy,Xb);
for n = 1:length(Xb)
    BaseList{n,5} = lbb(n);
    BaseList{n,6} = ubb(n); 
end


for n = 1:length(Xb)
    BaseList{n,4} = Xb(n);
end
Yraw.Base  =SplineData.P12.SA0.IA0.RawData.(strcat('FZ',string(Fz_nom))).MZ.*ftlbs_2_Nm;
Xraw.Base  =SplineData.P12.SA0.IA0.RawData.(strcat('FZ',string(Fz_nom))).SA.*Deg2Rad;
OutFig.Tabs.Base.Pure= uitab(OutFig.TabGroup.Pure,'Title','Base');
OutFig.Axes.Base.Pure = axes(OutFig.Tabs.Base.Pure);
hold(OutFig.Axes.Base.Pure,'on')
plot(OutFig.Axes.Base.Pure,Xraw.Base,Yraw.Base,'k.')
plot(OutFig.Axes.Base.Pure,Alpha,ydata,'LineWidth',1.5)
plot(OutFig.Axes.Base.Pure,Alpha,mzfit.Base,'LineWidth',1.5)
grid(OutFig.Axes.Base.Pure,'on')
title(OutFig.Axes.Base.Pure,'Base Fit')
legend(OutFig.Axes.Base.Pure,'Raw','Spline','Pacejka','Location','best')
% 
% %% dFz Parameter Fitting %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
ubfz = [0.015,  20,  20, 20,  20,  20, 270]'; % upper bounds for lsqcurvefit
lbfz = [-0.015, -70, -70, -50, -50, -50, -20]'; % lower bounds for lsqcurvefit

Fz  = Fz_vals.*4.448;
dfz = (Fz-Fz_0_prime)./Fz_0_prime;
[K_yalpha,Cy,mu_y,Dy,By,K_ygo,S_Hy,S_Vy,K_yalphag0,Fy_og0] = ParameterLoad(FYFileName,Fz_0_prime,0,Alpha_star,Fz,dfz );
dFzFit.K_yalpha_p = K_yalpha + epsilon.k;

dFzFit.S_Hf     = S_Hy + S_Vy./dFzFit.K_yalpha_p;
dFzFit.S_Ht     = @(Xf) Xb(1) + Xf(1).*dfz; %
dFzFit.alpha_t  = @(Xf) Alpha_star + dFzFit.S_Ht(Xf);
dFzFit.alpha_r  = @(Xf)  Alpha_star + dFzFit.S_Hf;
dFzFit.Bt       = @(Xf) (Xb(2) + Xf(2)*dfz + Xf(3).*(dfz.^2)).*(1+Xb(3));
dFzFit.Ct       = @(Xf) Xb(6);
dFzFit.Dto      = @(Xf) Fz.*(Ro./Fz_0_prime).*(Xb(7) + Xf(5).*dfz); 
dFzFit.Dt       = @(Xf) dFzFit.Dto(Xf).*(1);
dFzFit.Et       = @(Xf) (Xb(9) + Xf(7).*dfz).*(1 +(Xb(10)).*(2/pi).*atan(dFzFit.Bt(Xf).*dFzFit.Ct(Xf).*dFzFit.alpha_t(Xf)));%
dFzFit.Br       = @(Xf) (Xb(4) + Xb(5).*Cy.*By);
dFzFit.Cr       =    1;
dFzFit.Dr       = @(Xf) Fz.*Ro.*(Xb(8) + Xf(6).*dfz)*Cos_alph_p;
% dFzFit.Kzao     = @(Xf) dFzFit.Dto(Xf).*K_yalphag0;
% dFzFit.Kzgo     = @(Xf) Fz.*Ro(Xb(9)- dFzFit.Dto(Xf).*K_ygo); 
dFzFit.to       = @(Xf) dFzFit.Dt(Xf).*cos( dFzFit.Ct(Xf).*atan(dFzFit.Bt(Xf).*dFzFit.alpha_t(Xf)-dFzFit.Et(Xf).*(dFzFit.Bt(Xf).*dFzFit.alpha_t(Xf)- atan(dFzFit.Bt(Xf).*dFzFit.alpha_t(Xf))))).*Cos_alph_p;
dFzFit.Mzo_p    = @(Xf) -dFzFit.to(Xf).*Fy_og0;
dFzFit.Mzro     = @(Xf) dFzFit.Dr(Xf).*cos(dFzFit.Cr.*atan(dFzFit.Br(Xf).*dFzFit.alpha_t(Xf))).*Cos_alph_p;
dFzFit.Mzo      = @(Xf,Alpha_star) dFzFit.Mzo_p(Xf) +dFzFit.Mzro(Xf); 

MzVar = strcat('MZ_',TestID,'_',string(Fz_vals),'FZ_12P_0IA');
ydata =SplineData.P12.SA0.IA0.(MzVar).*ftlbs_2_Nm;
 
Xf = lsqcurvefit(dFzFit.Mzo,x0fz,Alpha_star,ydata,lbfz,ubfz,opts_base);
mzfit.dFz =feval(dFzFit.Mzo,Xf,Alpha_star);

% Check.dFz.S_Hy = feval(dFzFit.S_Hy,Xf);
% Check.dFz.mu_y = feval(dFzFit.mu_y,Xf);
% Check.dFz.C_y = feval(dFzFit.C_y,Xf);
% Check.dFz.D_y = feval(dFzFit.D_y,Xf);
 Check.dFzFit.ET = feval(dFzFit.Et,Xf);
% Check.dFz.Ky_a = feval(dFzFit.Ky_a,Xf);
% Check.dFz.B_y = feval(dFzFit.B_y,Xf);
% Check.dFz.H_y = feval(dFzFit.H_y,Xf);
% 
for n = 1:length(Xf)
    FzList{n,4} = Xf(n);
    FzList{n,5} = lbfz(n);
    FzList{n,6} = ubfz(n);
end
% 
Yraw.dFz  =SplineData.P12.SA0.IA0.RawData.(strcat('FZ',string(Fz_vals))).MZ.*ftlbs_2_Nm;
Xraw.dFz  =SplineData.P12.SA0.IA0.RawData.(strcat('FZ',string(Fz_vals))).SA.*Deg2Rad;
OutFig.Tabs.dFz.Pure= uitab(OutFig.TabGroup.Pure,'Title','dFz');
OutFig.Axes.dFz.Pure = axes(OutFig.Tabs.dFz.Pure);
hold(OutFig.Axes.dFz.Pure,'on')
plot(OutFig.Axes.dFz.Pure,Xraw.dFz,Yraw.dFz,'k.')
plot(OutFig.Axes.dFz.Pure,Alpha,ydata,'LineWidth',1.5)
plot(OutFig.Axes.dFz.Pure,Alpha,mzfit.dFz,'LineWidth',1.5)
grid(OutFig.Axes.dFz.Pure,'on')
title(OutFig.Axes.dFz.Pure,'dFz Fit')
legend(OutFig.Axes.dFz.Pure,'Raw','Spline','Pacejka','Location','best')

% %% dPi Parameters
% 
% for n = 1:length(x0dPi)
%     dPiList{n,4} = 0;
%     dPiList{n,5} = 0;
%     dPiList{n,6} = 0;
% end

%% dIA parameters
ubIA = [ 0.01,  20, 20,  20,  20,  20, 20]; 
lbIA = [-0.01, -20, -20, -20,  -20, -20, -50];

Fz  = Fz_nom.*4.448;
dfz = (Fz-Fz_0_prime)./Fz_0_prime;
[K_yalpha,Cy,mu_y,Dy,By,K_ygo,S_Hy,S_Vy,K_yalphag0,Fy_og0] = ParameterLoad(FYFileName,Fz_0_prime,gamma_star,Alpha_star,Fz,dfz );

dIAFit.K_yalpha_p = K_yalpha + epsilon.k;

dIAFit.S_Hf     = S_Hy + S_Vy./dIAFit.K_yalpha_p;
dIAFit.S_Ht     = @(XIA) Xb(1) + Xf(1).*dfz + (XIA(1)).*gamma_star; %
dIAFit.alpha_t  = @(XIA) Alpha_star + dIAFit.S_Ht(XIA);
dIAFit.alpha_r  = @(XIA)  Alpha_star + dIAFit.S_Hf;
dIAFit.Bt       = @(XIA) (Xb(2) + Xf(2)*dfz + Xf(3).*(dfz.^2)).*(1+Xb(3) + XIA(2).*abs(gamma_star));
dIAFit.Ct       = @(XIA) Xb(6);
dIAFit.Dto      = @(XIA) Fz.*(Ro./Fz_0_prime).*(Xb(7) + Xf(5).*dfz); 
dIAFit.Dt       = @(XIA) dIAFit.Dto(XIA).*(1 + XIA(3).*abs(gamma_star)+XIA(4).*(gamma_star.^2));
dIAFit.Et       = @(XIA) (Xb(9) + Xf(7).*dfz).*(1 +(Xb(10) + XIA(7).*gamma_star).*(2/pi).*atan(dIAFit.Bt(XIA).*dIAFit.Ct(XIA).*dIAFit.alpha_t(XIA)));%
dIAFit.Br       = @(XIA) (Xb(4) + Xb(5).*Cy.*By);
dIAFit.Cr       =    1;
dIAFit.Dr       = @(XIA) Fz.*Ro.*(Xb(8) + Xf(6).*dfz + ( (XIA(5)) + (XIA(6)).*abs(gamma_star)).*gamma_star)*Cos_alph_p;
% dIAFit.Kzao     = @(XIA) dIAFit.Dto(XIA).*K_yalphag0;
% dIAFit.Kzgo     = @(XIA) Fz.*Ro(Xb(9)- dIAFit.Dto(XIA).*K_ygo); 
dIAFit.to       = @(XIA) dIAFit.Dt(XIA).*cos( dIAFit.Ct(XIA).*atan(dIAFit.Bt(XIA).*dIAFit.alpha_t(XIA)-dIAFit.Et(XIA).*(dIAFit.Bt(XIA).*dIAFit.alpha_t(XIA)- atan(dIAFit.Bt(XIA).*dIAFit.alpha_t(XIA))))).*Cos_alph_p;
dIAFit.Mzo_p    = @(XIA) -dIAFit.to(XIA).*Fy_og0;
dIAFit.Mzro     = @(XIA) dIAFit.Dr(XIA).*cos(dIAFit.Cr.*atan(dIAFit.Br(XIA).*dIAFit.alpha_t(XIA))).*Cos_alph_p;
dIAFit.Mzo      = @(XIA,Alpha_star) dIAFit.Mzo_p(XIA) +dIAFit.Mzro(XIA); 

MZVar = strcat('MZ_',TestID,'_',string(Fz_nom),'FZ_12P_',string(gamma_vals),'IA');
ydata = SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).(MZVar).*ftlbs_2_Nm;


XIA = lsqcurvefit(dIAFit.Mzo,x0IA,Alpha_star,ydata,lbIA,ubIA,opts_base);
mzfit.dIA =feval(dIAFit.Mzo,XIA,Alpha_star);

for n = 1:length(XIA)
    IAList{n,4} = XIA(n);
    IAList{n,5} = lbIA(n);
    IAList{n,6} = ubIA(n);
end

Yraw.dIA  =SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).RawData.(strcat('FZ',string(Fz_nom))).MZ.*ftlbs_2_Nm;
Xraw.dIA  =SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).RawData.(strcat('FZ',string(Fz_nom))).SA.*Deg2Rad;
OutFig.Tabs.dIA.Pure= uitab(OutFig.TabGroup.Pure,'Title','dIA');
OutFig.Axes.dIA.Pure = axes(OutFig.Tabs.dIA.Pure);
hold(OutFig.Axes.dIA.Pure,'on')
plot(OutFig.Axes.dIA.Pure,Xraw.dIA,Yraw.dIA,'k.')
plot(OutFig.Axes.dIA.Pure,Alpha,ydata,'LineWidth',1.5)
plot(OutFig.Axes.dIA.Pure,Alpha,mzfit.dIA,'LineWidth',1.5)
grid(OutFig.Axes.dIA.Pure,'on')
title(OutFig.Axes.dIA.Pure,'dIA Fit')
legend(OutFig.Axes.dIA.Pure,'Spline','Pacejka','Location','best')

% 
% %% dIA and dFz parameters
ubIAFz = [ 0.01,10,  10];
lbIAFz = [-0.01,-10, -10];

Fz  = Fz_vals.*4.448;
dfz = (Fz-Fz_0_prime)./Fz_0_prime;
[K_yalpha,Cy,mu_y,Dy,By,K_ygo,S_Hy,S_Vy,K_yalphag0,Fy_og0] = ParameterLoad(FYFileName,Fz_0_prime,gamma_star,Alpha_star,Fz,dfz );

dIAFzFit.K_yalpha_p = K_yalpha + epsilon.k;
dIAFzFit.S_Hf     = S_Hy + S_Vy./dIAFzFit.K_yalpha_p;
dIAFzFit.S_Ht     = @(XIAFz) Xb(1) + Xf(1).*dfz + (XIA(1)+XIAFz(1).*dfz).*gamma_star ; %
dIAFzFit.alpha_t  = @(XIAFz) Alpha_star + dIAFzFit.S_Ht(XIAFz);
dIAFzFit.alpha_r  = @(XIAFz)  Alpha_star + dIAFzFit.S_Hf;
dIAFzFit.Bt       = @(XIAFz) (Xb(2) + Xf(2)*dfz + Xf(3).*(dfz.^2)).*(1 + Xb(3)   + (XIA(2).*abs(gamma_star)) );%
dIAFzFit.Ct       = @(XIAFz) Xb(6);
dIAFzFit.Dto      = @(XIAFz) Fz.*(Ro./Fz_0_prime).*(Xb(7) + Xf(5).*dfz); 
dIAFzFit.Dt       = @(XIAFz) dIAFzFit.Dto(XIAFz).*(1 + XIA(3).*abs(gamma_star) + XIA(4).*(gamma_star.^2));%
dIAFzFit.Et       = @(XIAFz) (Xb(9) + Xf(7).*dfz).*(1 +(Xb(10) + XIA(7).*gamma_star).*(2/pi).*atan(dIAFzFit.Bt(XIAFz).*dIAFzFit.Ct(XIAFz).*dIAFzFit.alpha_t(XIAFz))); 
dIAFzFit.Br       = @(XIAFz) (Xb(4) + Xb(5).*Cy.*By);
dIAFzFit.Cr       =    1;
dIAFzFit.Dr       = @(XIAFz) Fz.*Ro.*((Xb(8) + Xf(6).*dfz) + ( (XIA(5)+ XIAFz(2).*dfz) + (XIA(6)+XIAFz(3).*dfz).*abs(gamma_star)).*gamma_star )*Cos_alph_p;
% dIAFzFit.Kzao     = @(XIAFz) dIAFzFit.Dto(XIAFz).*K_yalphag0;
% dIAFzFit.Kzgo     = @(XIAFz) Fz.*Ro(Xb(9)- dIAFzFit.Dto(XIAFz).*K_ygo); 
dIAFzFit.to       = @(XIAFz) dIAFzFit.Dt(XIAFz).*cos( dIAFzFit.Ct(XIAFz).*atan(dIAFzFit.Bt(XIAFz).*dIAFzFit.alpha_t(XIAFz)-dIAFzFit.Et(XIAFz).*(dIAFzFit.Bt(XIAFz).*dIAFzFit.alpha_t(XIAFz)- atan(dIAFzFit.Bt(XIAFz).*dIAFzFit.alpha_t(XIAFz))))).*Cos_alph_p;
dIAFzFit.Mzo_p    = @(XIAFz) -dIAFzFit.to(XIAFz).*Fy_og0;
dIAFzFit.Mzro     = @(XIAFz) dIAFzFit.Dr(XIAFz).*cos(dIAFzFit.Cr.*atan(dIAFzFit.Br(XIAFz).*dIAFzFit.alpha_t(XIAFz))).*Cos_alph_p;
dIAFzFit.Mzo      = @(XIAFz,Alpha_star) dIAFzFit.Mzo_p(XIAFz) +dIAFzFit.Mzro(XIAFz);  

MZVar = strcat('MZ_',TestID,'_',string(Fz_vals),'FZ_12P_',string(gamma_vals),'IA');
ydata = SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).(MZVar).*ftlbs_2_Nm; 
  
XIFz= lsqcurvefit(dIAFzFit.Mzo,x0IAFz,Alpha_star,ydata,lbIAFz,ubIAFz,opts_base);
mzfit.dIAFz =feval(dIAFzFit.Mzo,XIFz,Alpha_star);

for n = 1:length(XIFz)
    IAdFzList{n,4} = XIFz(n);
    IAdFzList{n,5} = lbIAFz(n);
    IAdFzList{n,6} = ubIAFz(n);
end

Yraw.dIAFz  =SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).RawData.(strcat('FZ',string(Fz_vals))).MZ.*ftlbs_2_Nm;
Xraw.dIAFz  =SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).RawData.(strcat('FZ',string(Fz_vals))).SA.*Deg2Rad;

OutFig.Tabs.dIAFz.Pure= uitab(OutFig.TabGroup.Pure,'Title','dIAFz');
OutFig.Axes.dIAFz.Pure = axes(OutFig.Tabs.dIAFz.Pure);
hold(OutFig.Axes.dIAFz.Pure,'on')
plot(OutFig.Axes.dIAFz.Pure,Xraw.dIAFz,Yraw.dIAFz,'k.')
plot(OutFig.Axes.dIAFz.Pure,Alpha,ydata,'LineWidth',1.5)
plot(OutFig.Axes.dIAFz.Pure,Alpha,mzfit.dIAFz,'LineWidth',1.5)
grid(OutFig.Axes.dIAFz.Pure,'on')
title(OutFig.Axes.dIAFz.Pure,'dIAFz Fit')
legend(OutFig.Axes.dIAFz.Pure,'Spline','Pacejka','Location','best')

     
% 

MZ_ParameterList = [BaseList;FzList;IAList;IAdFzList];

MZ_ParameterList  = cell2table(MZ_ParameterList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});     
FileName = strcat('MZ_Parameters','_',Tire,'_',string(Round),'_',string(Run),'_', string(Fz_nom),'FZ','.mat');
save(strcat("CC's tire model folder\Fitted Parameters\",FileName),'MZ_ParameterList')


function [K_yalpha,Cy,mu_y,Dy,By,K_ygo,S_Hy,S_Vy,K_yalphag0,Fy_og0] = ParameterLoad(FYFileName,Fz_0_prime,gamma_star,Alpha_star,Fz,dfz ) 
   data = load (strcat("CC's tire model folder\Fitted Parameters\", FYFileName));
   assignin('base', 'FY_ParameterList', data.FY_ParameterList);
   ParameterList = data.FY_ParameterList;
   
   p = struct();
 
   
   for n = 1:height(ParameterList) 
       if strcmp(ParameterList.Structure{n,1},'p.') == 1
           p.(ParameterList.Variable{n,1}) = (ParameterList.Final(n,1));
       end
   end
   Lam.mu_y_star = 1; 
   epsilon.y = 0.1;
   epsilon.k = 0.1;
   dpi = 0;
   
   S.Vy_gamma = Fz.*(p.Vsy3 + p.Vsy4.*dfz).*gamma_star;
   K_yalpha   = p.Ky1.*Fz_0_prime.*(1+p.py1.*dpi).*(1-p.Ky3.*abs(gamma_star)).*sin(p.Ky4.*atan((Fz./Fz_0_prime)./((p.Ky2+p.Ky5.*gamma_star.^2).*(1+p.py2.*dpi))));   
   K_ygo      = Fz.*(p.Ky6 + p.Ky7.*dfz); 
   S_Hy       = (p.Hsy1 +p.Hsy2.*dfz) + (K_ygo.*gamma_star-S.Vy_gamma)./(K_yalpha+epsilon.k);
   Cy         = p.Cy1;
   mu_y       = ((p.Dy1+p.Dy2.*dfz).*(1+p.py3.*dpi+p.py4.*(dpi.^2)).*(1-p.Dy3.*(gamma_star.^2))).*Lam.mu_y_star;
   Dy         = mu_y.*Fz;
   By         = K_yalpha./(Cy.*Dy+epsilon.y);   
   S_Vy       = Fz.*(p.Vsy1 + p.Vsy2.*dfz) +S.Vy_gamma;
   gamma_star = 0;
   % Parameters for gamma = 0     
   K_yalphag0   = p.Ky1.*Fz_0_prime.*(1+p.py1.*dpi).*(1-p.Ky3.*abs(gamma_star)).*sin(p.Ky4.*atan((Fz./Fz_0_prime)./((p.Ky2+p.Ky5.*gamma_star.^2).*(1+p.py2.*dpi))));
   S.Vy_gammag0 = Fz.*(p.Vsy3 + p.Vsy4.*dfz).*gamma_star;
   K_ygog0      = Fz.*(p.Ky6 + p.Ky7.*dfz);
   S_Hyg0       = (p.Hsy1 +p.Hsy2.*dfz) + (K_ygog0.*gamma_star-S.Vy_gammag0)./(K_yalphag0+epsilon.k);
   alpha_yg0    = Alpha_star+S_Hyg0 ;
   Cyg0         = p.Cy1;%+p.Cy2.*dfz;
   mu_yg0       = ((p.Dy1+p.Dy2.*dfz).*(1+p.py3.*dpi+p.py4.*(dpi.^2)).*(1-p.Dy3.*(gamma_star.^2))).*Lam.mu_y_star;
   Dyg0         = mu_yg0.*Fz;
   Eyg0         = (p.Ey1+p.Ey2.*dfz).*(1+p.Ey5.*gamma_star.^2-(p.Ey3+p.Ey4.*gamma_star).*sign(Alpha_star));
   Byg0         = K_yalphag0./(Cyg0.*Dyg0+epsilon.y);
   
   S_Vyg0       = Fz.*(p.Vsy1 + p.Vsy2.*dfz) +S.Vy_gammag0;
   Fy_og0        = Dyg0.*sin(Cyg0.*atan(Byg0.*alpha_yg0-Eyg0.*(Byg0.*alpha_yg0-atan(Byg0.*alpha_yg0))))+S_Vyg0;
end
end