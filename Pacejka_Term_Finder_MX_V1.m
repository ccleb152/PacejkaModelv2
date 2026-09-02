% V3 includes combined slip fits
clearvars
clc
%% Test Information
Round  = 9;
FyRun    = 32;
FxRun    = 72;
TestID = strcat('R',string(Round),'_Rn',string(FyRun));
Type = 'Fy';
TireMan = 'Hoosier';
Tire   = 'R20_6_18_10';

% Parameter Values
P = 12;
Fz_vals = [150];
gamma_vals = [2];
 
%% FY Test Information
FYFileName = strcat('FY_Parameters','_',Tire,'_',string(Round),'_',string(FyRun),'.mat');
FXFileName = strcat('FX_Parameters','_',Tire,'_',string(Round),'_',string(FxRun),'.mat');
%% Fit Options
opts = optimset('TolFun',1e-8,'MaxFunEvals',120000,'MaxIter',120000,'TolX',1e-8); 
addpath(genpath('FY Data'))
addpath(genpath('FX Data'))
[SplineData] = Raw_Data_Fitter_Mx_V2(Round,FyRun,Tire);

%% Fit Data Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Fz_nom = 150;
Ro = 9*0.0254;
Fz   =  Fz_nom .*4.448; %(N)
p_i   = 12*82.737;  %(kPa)
gamma = gamma_vals*pi./180; %(rad)

%% Conversions %%%%
Deg2Rad = pi./180;
ftlbs_2_Nm = 0.3048*4.448;
%% Base Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
V = 25*1.609/3.6;
Fz_0 = 150.*4.448;
pio = 12*82.737;  %(kPa)
rl = 8.67*0.0254; %(m)
Alpha = SplineData.P12.SA0.IA0.SA_R9_Rn32_150FZ_12P_0IA.*Deg2Rad;

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

     q0.sx1  = 10;     qstat.sx1  = [1 0 0 0 0];
     q0.sx2  = -10;    qstat.sx2  = [0 0 1 0 0];
     q0.sx3  = 1;     qstat.sx3  = [1 0 0 0 0];
     q0.sx4  = 1;     qstat.sx4  = [1 0 0 0 0];
     
     q0.sx5  = 1;     qstat.sx5  = [1 0 0 0 0];
     q0.sx6  = 0.01;     qstat.sx6  = [1 0 0 0 0];
     q0.sx7  = -1;    qstat.sx7  = [0 0 1 0 0];
     q0.sx8  = 1;     qstat.sx8  = [1 0 0 0 0];
     q0.sx9  = 2;     qstat.sx9  = [1 0 0 0 0];
     q0.sx10 = 1;     qstat.sx10 = [0 0 1 0 0];
     q0.sx11 = 1;     qstat.sx11 = [0 0 1 0 0];
    
     
     
     
    epsilon.y = 0.1;
    epsilon.k = 0.1;
    Zeta.z2 = 1;       
    Zeta.z3 = 1;
%% Parameter Lists
 
Ques     =  [repelem({'q0.'},length(fieldnames(q0)),1), fieldnames(q0)];
%Arrs     =  [repelem({'r0.'},length(fieldnames(r0)),1), fieldnames(r0)];
MX_ParameterList = [Ques];%; Arrs];
x0 = zeros(length(MX_ParameterList),1);

for n = 1:length(MX_ParameterList) 
    var = strcat( MX_ParameterList{n,1}, MX_ParameterList{n,2} );
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

for n = 1:length(MX_ParameterList)
    var = MX_ParameterList{n,2};
    if contains(MX_ParameterList{n,1},'q0.') == 1
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
 [Fy_cn] = ParameterLoad(FYFileName,FXFileName,Fz_0_prime,0,Alpha_star,Fz,dfz);
 
ubb = [ 5,  5,  1,  1,  0.01,  1, 0.01]';
lbb = [-0.025, 0, 1, 1, -0.01, 1, -0.01]';

MxVar = strcat('MX_',TestID,'_',string(Fz_nom),'FZ_12P_0IA');
ydata =SplineData.P12.SA0.IA0.(MxVar).*ftlbs_2_Nm;
Yraw.Base  =SplineData.P12.SA0.IA0.RawData.(strcat('FZ',string(Fz_nom))).MX.*ftlbs_2_Nm;
Xraw.Base  =SplineData.P12.SA0.IA0.RawData.(strcat('FZ',string(Fz_nom))).SA.*Deg2Rad;
OutFig.Tabs.Base.Pure= uitab(OutFig.TabGroup.Pure,'Title','Base');
OutFig.Axes.Base.Pure = axes(OutFig.Tabs.Base.Pure);
hold(OutFig.Axes.Base.Pure,'on')
plot(OutFig.Axes.Base.Pure,Xraw.Base,Yraw.Base,'k.')
plot(OutFig.Axes.Base.Pure,Alpha,ydata,'LineWidth',1.5)

for n = 1:10
BaseFit.Mxo = @(Xb,Alpha_star) Ro.*Fz.*(Xb(1) + Xb(2)*(Fy_cn./Fz_0_prime) + Xb(3).*cos(Xb(4).*atan(Xb(5).*(Fz./Fz_0_prime)).^2).*sin( Xb(6).*atan(Xb(7).*(Fy_cn./Fz_0_prime))));



opts_base = optimset('TolFun',1e-8,'MaxFunEvals',4000000 ,'MaxIter',4000000 ,'TolX',1e-8,'FinDiffType','central'); 
Xb = lsqcurvefit(BaseFit.Mxo,x0b,Alpha_star,ydata,lbb,ubb,opts_base);
Xbn(:,n) = Xb; 

x0b = Xb;

yfit.Base =feval(BaseFit.Mxo ,Xb,Alpha_star);

plot(OutFig.Axes.Base.Pure,Alpha,yfit.Base,'LineWidth',1.5)
grid(OutFig.Axes.Base.Pure,'on')
title(OutFig.Axes.Base.Pure,'Base Fit')
legend(OutFig.Axes.Base.Pure,'Raw','Spline','Pacejka','Location','best')
 
end
% Check.Base.S_Hy = feval(BaseFit.S_Hy,Xb);
% Check.Base.mu_y = feval(BaseFit.mu_y,Xb);
% Check.Base.C_y = feval(BaseFit.C_y,Xb);
% Check.Base.D_y = feval(BaseFit.D_y,Xb);
%  Check.Base.ET = feval(BaseFit.Et,Xb);
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

% %% dIA parameters
 [Fy_cn] = ParameterLoad(FYFileName,FXFileName,Fz_0_prime,gamma_star,Alpha_star,Fz,dfz);
 
ubIA = [ 100,  100,  100,  10]';
lbIA = [-100, -100, -100, -100]';


dIAFit.Mxo = @(XIA,Alpha_star) Ro.*Fz.*(Xb(1) - XIA(1).*gamma + Xb(2)*(Fy_cn./Fz_0_prime) + Xb(3).*cos(Xb(4).*atan(Xb(5).*(Fz./Fz_0_prime)).^2).*sin(XIA(2).*gamma + Xb(6).*atan(Xb(7).*(Fy_cn./Fz_0_prime)))+ XIA(3).*atan(XIA(4).*Fz./Fz_0_prime));


MXVar = strcat('MX_',TestID,'_',string(Fz_nom),'FZ_12P_',string(gamma_vals),'IA');
ydata = SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).(MXVar).*ftlbs_2_Nm;
opts_base = optimset('TolFun',1e-8,'MaxFunEvals',400000 ,'MaxIter',400000 ,'TolX',1e-8,'FinDiffType','central'); 
XIA = lsqcurvefit(dIAFit.Mxo,x0IA,Alpha_star,ydata,lbIA,ubIA,opts_base);
 


 
yfit.dIA =feval(dIAFit.Mxo,XIA,Alpha_star);

for n = 1:length(XIA)
    IAList{n,4} = XIA(n);
    IAList{n,5} = lbIA(n);
    IAList{n,6} = ubIA(n);
end

Yraw.dIA  =SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).RawData.(strcat('FZ',string(Fz_nom))).MX.*ftlbs_2_Nm;
Xraw.dIA  =SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).RawData.(strcat('FZ',string(Fz_nom))).SA.*Deg2Rad;
OutFig.Tabs.dIA.Pure= uitab(OutFig.TabGroup.Pure,'Title','dIA');
OutFig.Axes.dIA.Pure = axes(OutFig.Tabs.dIA.Pure);
hold(OutFig.Axes.dIA.Pure,'on')
plot(OutFig.Axes.dIA.Pure,Xraw.dIA,Yraw.dIA,'k.')
plot(OutFig.Axes.dIA.Pure,Alpha,ydata,'LineWidth',1.5)
plot(OutFig.Axes.dIA.Pure,Alpha,yfit.dIA,'LineWidth',1.5)
grid(OutFig.Axes.dIA.Pure,'on')
title(OutFig.Axes.dIA.Pure,'dIA Fit')
legend(OutFig.Axes.dIA.Pure, 'Raw','Spline','Pacejka','Location','best')
 
     


MX_ParameterList = [BaseList;IAList];

MX_ParameterList  = cell2table(MX_ParameterList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});     
FileName = strcat('MX_Parameters','_',Tire,'_',string(Round),'_',string(FyRun),'.mat');
save(strcat("CC's tire model folder\Fitted Parameters\",FileName),'MX_ParameterList')


function  [Fy_cn] = ParameterLoad(FYFileName,FXFileName,Fz_0_prime,gamma_star,Alpha_star,Fz,dfz)
   load(strcat("CC's tire model folder\Fitted Parameters\",FYFileName));
   load(strcat("CC's tire model folder\Fitted Parameters\",FXFileName));
   ParameterList = [FY_ParameterList;FX_ParameterList];
   
   p = struct();
 
   kappa = 0;
   for n = 1:height(ParameterList) 
       if strcmp(ParameterList.Structure{n,1},'p.') == 1
           p.(ParameterList.Variable{n,1}) = (ParameterList.Final(n,1));
       elseif strcmp(ParameterList.Structure{n,1},'ry.') == 1
           r.(ParameterList.Variable{n,1}) = (ParameterList.Final(n,1));
       end
   end
   Lam.mu_y_star = 1; 
   epsilon.y = 0.1;
   epsilon.k = 0.1;
   dpi = 0;
   
%    S.Vy_gamma = Fz.*(p.Vsy3 + p.Vsy4.*dfz).*gamma_star;
%    K_yalpha   = p.Ky1.*Fz_0_prime.*(1+p.py1.*dpi).*(1-p.Ky3.*abs(gamma_star)).*sin(p.Ky4.*atan((Fz./Fz_0_prime)./((p.Ky2+p.Ky5.*gamma_star.^2).*(1+p.py2.*dpi))));   
%    K_ygo      = Fz.*(p.Ky6 + p.Ky7.*dfz); 
%    S_Hy       = (p.Hsy1 +p.Hsy2.*dfz) + (K_ygo.*gamma_star-S.Vy_gamma)./(K_yalpha+epsilon.k);
%    Cy         = p.Cy1;
%    mu_y       = ((p.Dy1+p.Dy2.*dfz).*(1+p.py3.*dpi+p.py4.*(dpi.^2)).*(1-p.Dy3.*(gamma_star.^2))).*Lam.mu_y_star;
%    Dy         = mu_y.*Fz;
%    By         = K_yalpha./(Cy.*Dy+epsilon.y);   
%    S_Vy       = Fz.*(p.Vsy1 + p.Vsy2.*dfz) +S.Vy_gamma;
%  
   % Parameters for gamma = 0     
   K_yalpha   = p.Ky1.*Fz_0_prime.*(1+p.py1.*dpi).*(1-p.Ky3.*abs(gamma_star)).*sin(p.Ky4.*atan((Fz./Fz_0_prime)./((p.Ky2+p.Ky5.*gamma_star.^2).*(1+p.py2.*dpi))));
   S.Vy_gamma = Fz.*(p.Vsy3 + p.Vsy4.*dfz).*gamma_star;
   K_ygo      = Fz.*(p.Ky6 + p.Ky7.*dfz);
   S_Hy       = (p.Hsy1 +p.Hsy2.*dfz) + (K_ygo.*gamma_star-S.Vy_gamma)./(K_yalpha+epsilon.k);
   alpha_y    = Alpha_star+S_Hy ;
   Cy         = p.Cy1;
   mu_y       = ((p.Dy1+p.Dy2.*dfz).*(1+p.py3.*dpi+p.py4.*(dpi.^2)).*(1-p.Dy3.*(gamma_star.^2))).*Lam.mu_y_star;
   Dy         = mu_y.*Fz;
   Ey         = (p.Ey1+p.Ey2.*dfz).*(1+p.Ey5.*gamma_star.^2-(p.Ey3+p.Ey4.*gamma_star).*sign(Alpha_star));
   By         = K_yalpha./(Cy.*Dy+epsilon.y);
   
   S_Vy       = Fz.*(p.Vsy1 + p.Vsy2.*dfz) +S.Vy_gamma;
   Fy_o        = Dy.*sin(Cy.*atan(By.*alpha_y-Ey.*(By.*alpha_y-atan(By.*alpha_y))))+S_Vy;
   
   B_yk = (r.By1 + r.By4.*(gamma_star.^2)).*cos(atan(r.By2.*(Alpha_star-r.By3)));
   C_yk  = r.Cy1;
   E_yk  = r.Ey1 + r.Ey2.*dfz;
   S_Hyk = (r.Hsy1 +r.Hsy2.*dfz);
   D_Vyk = mu_y.*Fz.*(r.Vsy1 + r.Vsy2.*dfz + r.Vsy3.*gamma_star).*cos(atan(r.Vsy4.*Alpha_star));
   S_Vyk = D_Vyk.*sin(r.Vsy5.*atan(r.Vsy6.*kappa));
   kappa_s = kappa + S_Hyk;
   G_yko = cos(C_yk.*atan(B_yk.*S_Hyk-E_yk.*(B_yk.*S_Hyk-atan(B_yk.*S_Hyk))));
   G_yk = cos(C_yk.*atan(B_yk.*kappa_s-E_yk.*(B_yk.*kappa_s-atan(B_yk.*kappa_s))))./G_yko ;
   Fy_cn =G_yk.*Fy_o + S_Vyk;

end