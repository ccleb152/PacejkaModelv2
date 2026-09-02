% FX Pacejka Term Finder
% V3 includes combined slip fits
% V4 includes combined slip lateral fits

function [FX_ParameterList, yfit, kappa] = Pacejka_Term_Finder_FX_V4_Redo(Round, Run, Tire, Fz_nom)
%% Test Information
TestID = strcat('R',string(Round),'_Rn',string(Run));
Type = 'FX';
TireMan = 'Hoosier';


% Parameter Values
P = 12;
Fz_vals = [50];
gamma_vals = [2];
SA_vals  = 0;

%% Fit Options
opts = optimset('TolFun',1e-8,'MaxFunEvals',80000,'MaxIter',80000,'TolX',1e-8); 
addpath(genpath('FX Data'))
[SplineData] = Raw_Data_Fitter_Fx_V2(Round,Run,Tire);

[RawData] = Pacejka_Term_Finder_Data_Compiler_V1(Round, Run,Tire); 
%Pacejka_Term_Finder_Data_Compiler_V1
%RawData = load('BaselineFit_Data.mat');
% FitData_IA_2 =  load('BaselineFit_Data_IA_2.mat');

% RawData.FX_Fit_N = RawData.FX_Fit_150.*4.448;


%% Fit Data Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
Fz   =  Fz_nom .*4.448; %(N)
p_i   = 12*82.737;  %(kPa)
gamma =2*pi./180; %(rad)

%% Base Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
V = 25*1.609/3.6;
Fz_0 = Fz_nom .*4.448;
pio = 12*82.737;  %(kPa)
rl = 8.67*0.0254; %(m)

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

%% 
Fz_0_prime = Lam.Fz_0.*Fz_0;
dpi = (p_i-pio)./pio;
dfz = (Fz-Fz_0_prime)./Fz_0_prime;


%% Initial Fit Parameters (Pstat = [isBase, is*dFz, is*Ia, is*dPi])
% Pure Longitudinal Slip Terms
p0.Cx1 = 1.5;    Pstat.Cx1 = [1,0,0,0];
% p0.Cx2 = 0.1;    Pstat.Cx2 = [1,0,0,0];

p0.Dx1 = 3.3;    Pstat.Dx1 = [1,0,0,0];
p0.Dx2 = -1.750; Pstat.Dx2 = [0,1,0,0]; % Linear Change in max mu with dFz
p0.Dx3 = 2;      Pstat.Dx3 = [0,0,1,0];

p0.px1 = 0;      Pstat.px1 = [0,0,0,1];
p0.px2 = 0;      Pstat.px2 = [0,0,0,1];        
p0.px3 = 0;      Pstat.px3 = [0,0,0,1];    
p0.px4 = 0;      Pstat.px4 = [0,0,0,1];    

p0.Ex1 = 0.4;    Pstat.Ex1 = [1,0,0,0];    
p0.Ex2 = -0.04;  Pstat.Ex2 = [0,1,0,0];   
p0.Ex3 = -0.4;   Pstat.Ex3 = [0,1,0,0];   
p0.Ex4 = 1.2;    Pstat.Ex4 = [1,0,0,0];   
% p0.Ex5 = 0.0525; Pstat.Ex5 = [1,0,0,0]; % Not part of original pacejika model 

p0.Kx1  = 60;   Pstat.Kx1 = [1,0,0,0]; 
p0.Kx2  = -10;   Pstat.Kx2 = [0,1,0,0]; 
p0.Kx3  = -0.1;  Pstat.Kx3 = [0,1,0,0]; 
 
% p0.Hx1 =-14.323; Pstat.Hx1 = [1,0,0,0]; 
% p0.Hx2 =-33;     Pstat.Hx2 = [0,1,0,0]; 
 

p0.Hsx1 = 0.0;     Pstat.Hsx1 = [1,0,0,0];  
p0.Hsx2 = 0.0;     Pstat.Hsx2 = [0,1,0,0];   

p0.Vsx1 = 0;     Pstat.Vsx1 = [1,0,0,0];  
p0.Vsx2 = 0;     Pstat.Vsx2 = [0,1,0,0]; 

% Combined Longitudinal Slip Terms
r0.Bx1 = 1;      Rstat.Bx1 = [1,0,0,0];  
r0.Bx2 = 1;      Rstat.Bx2 = [1,0,0,0];     
r0.Bx3 = 0;      Rstat.Bx3 = [0,0,1,0];     

r0.Cx1 = 1;      Rstat.Cx1 = [1,0,0,0]; 

r0.Ex1 = 1;      Rstat.Ex1 = [1,0,0,0]; 
r0.Ex2 = 1;      Rstat.Ex2 = [0,1,0,0]; 

r0.Hsx1 =0;      Rstat.Hsx1 = [1,0,0,0]; 

% Combined Lateral Slip Terms
ry0.By1 = 1;     Rystat.By1 = [1,0,0,0]; 
ry0.By2 = 1;     Rystat.By2 = [1,0,0,0];
ry0.By3 = 1;     Rystat.By3 = [1,0,0,0];
ry0.By4 = 1;     Rystat.By4 = [0,0,1,0];

ry0.Cy1 = 1;     Rystat.Cy1 = [1,0,0,0];

ry0.Ey1 = 1;     Rystat.Ey1 = [1,0,0,0];
ry0.Ey2 = 1;     Rystat.Ey2 = [0,1,0,0];

ry0.Hsy1 = 1;    Rystat.Hsy1 = [1,0,0,0];
ry0.Hsy2 = 1;    Rystat.Hsy2 = [0,1,0,0];
% ry0.Hsy3 = 1;    Rystat.Hsy3 = [0,0,1,0];

ry0.Vsy1 = 1;    Rystat.Vsy1 = [1,0,0,0];
ry0.Vsy2 = 1;    Rystat.Vsy2 = [0,1,0,0];
ry0.Vsy3 = 1;    Rystat.Vsy3 = [0,0,1,0];
ry0.Vsy4 = 1;    Rystat.Vsy4 = [1,0,0,0];
ry0.Vsy5 = 1;    Rystat.Vsy5 = [1,0,0,0];
ry0.Vsy6 = 1;    Rystat.Vsy6 = [1,0,0,0];

% Other terms
epsilon.x = 0.001;

Zeta.z1 = 1;

%% Parameter Lists
 
Pees     =  [repelem({'p0.'},length(fieldnames(p0)),1), fieldnames(p0)];
Arrs     =  [repelem({'r0.'},length(fieldnames(r0)),1), fieldnames(r0)];
Arr_whys =  [repelem({'ry0.'},length(fieldnames(ry0)),1), fieldnames(ry0)];
ParameterList = [Pees; Arrs; Arr_whys];
x0 = zeros(length(ParameterList),1);

for n = 1:length(ParameterList) 
    var = strcat( ParameterList{n,1}, ParameterList{n,2} );
    x0(n,1) = eval(var);
end


%% Output Figure Creation 
% Pure Slip Output Figure % 
OutFig.Fig.Pure = figure(1);
clf(OutFig.Fig.Pure)
OutFig.Fig.Pure.Name = 'Pure Slip Fitting Results';

OutFig.TabGroup.Pure= uitabgroup(OutFig.Fig.Pure);

% Combined Slip Output Figure %
OutFig.Fig.Comb = figure(2);
clf(OutFig.Fig.Comb )
OutFig.Fig.Comb.Name = 'Combined Slip Fitting Results';
OutFig.TabGroup.Comb = uitabgroup(OutFig.Fig.Comb);

%% Base Constants For Nominal Load and Zero Inlincation Angle (Negates all terms multiplied by dFz, gamma(IA), or dPi)
m = 0;
q = 0;
j = 0;
r = 0;
s = 0;
t = 0;
u = 0;
v = 0;
w = 0;
b = 0;
for n = 1:length(ParameterList)
    var = ParameterList{n,2};
    if contains(ParameterList{n,1},'p0.') == 1
        if Pstat.(var)(1) == 1
            m = m +1;
            BaseList{m,1} = 'p.';
            BaseList{m,2} = var;
            BaseList{m,3} = x0(n,1);
            x0b(m,1) = x0(n,1);

        elseif Pstat.(var)(2) == 1
             q = q +1;
            FzList{q,1} = 'p.';
            FzList{q,2} = var;
            FzList{q,3} = x0(n,1);
            x0fz(q,1) = x0(n,1);

        elseif Pstat.(var)(3) == 1
             j = j +1;
            IAList{j,1} = 'p.';
            IAList{j,2} = var;
            IAList{j,3} = x0(n,1);
            x0IA(j,1) = x0(n,1);
            
        elseif Pstat.(var)(4) == 1
             b = b +1;
            dPiList{b,1} = 'p.';
            dPiList{b,2} = var;
            dPiList{b,3} = x0(n,1);
            x0dPi(b,1) = x0(n,1);    
        end
    elseif contains(ParameterList{n,1},'r0.') == 1
        if Rstat.(var)(1) == 1
            r = r +1;
            CombBaseList{r,1} = 'r.';
            CombBaseList{r,2} = var;
            CombBaseList{r,3} = x0(n,1);
            xc0b(r,1) = x0(n,1);
        elseif Rstat.(var)(2) == 1
             s = s +1;
            CombFzList{s,1} = 'r.';
            CombFzList{s,2} = var;
            CombFzList{s,3} = x0(n,1);
            xc0fz(s,1) = x0(n,1);
        elseif Rstat.(var)(3) == 1
             t = t +1;
            CombIAList{t,1} = 'r.';
            CombIAList{t,2} = var;
            CombIAList{t,3} = x0(n,1);
            xc0IA(t,1) = x0(n,1);
        end
        
    elseif contains(ParameterList{n,1},'ry0.') == 1
        if Rystat.(var)(1) == 1
            u = u +1;
            FyBaseList{u,1} = 'ry.';
            FyBaseList{u,2} = var;
            FyBaseList{u,3} = x0(n,1);
            yc0b(u,1) = x0(n,1);
        elseif Rystat.(var)(2) == 1
             v = v +1;
            FyFzList{v,1} = 'ry.';
            FyFzList{v,2} = var;
            FyFzList{v,3} = x0(n,1);
            yc0fz(v,1) = x0(n,1);
        elseif Rystat.(var)(3) == 1
             w = w +1;
            FyIAList{w,1} = 'ry.';
            FyIAList{w,2} = var;
            FyIAList{w,3} = x0(n,1);
            yc0IA(w,1) = x0(n,1);
        end
    end
            
end
% ubb = [2,   2.85, -0.1,    0,    500,  0.001,   50];
% lbb = [1.4, 2.7, -0.5, -0.01, 0,    -0.001 , -50];
ubb = [2.2, 3.0,  0.2,  0.1,  600,  0.01,  100]; % Increased limits
lbb = [1.2, 2.5, -0.6, -0.1,  0,   -0.01, -100]; % Reduced limits

kappa = SplineData.P12.SA0.IA0.SL_R9_Rn72_150FZ_12P_0IA;

Base.S_Hx    = @(Xb)   Xb(6);    % Horizontal Offset
Base.mu_x    = @(Xb)   Xb(2);     % Base Mu value

Base.kappa_x = @(Xb) kappa + Base.S_Hx(Xb);
Base.C_x     = @(Xb) Xb(1);
Base.D_x     = @(Xb) Base.mu_x(Xb).*Fz.*Zeta.z1;
Base.E_x     = @(Xb) Xb(3).*(1-Xb(4).*sign(kappa));
Base.K_x     = @(Xb) Fz*Xb(5);
Base.B_x     = @(Xb) Base.K_x(Xb)./(Base.C_x(Xb).*Base.D_x(Xb)+epsilon.x);
Base.S_Vx    = @(Xb) Fz.*Xb(7);
 
Base.F_x     = @(Xb,kappa) Base.D_x(Xb).*sin(Base.C_x(Xb).*atan(Base.B_x(Xb).*Base.kappa_x(Xb) -Base.E_x(Xb).*(Base.B_x(Xb).*Base.kappa_x(Xb)-atan(Base.B_x(Xb).*Base.kappa_x(Xb))))) + Base.S_Vx(Xb);
FxVar = strcat('FX_',TestID,'_',string(Fz_nom),'FZ_12P_0IA');
ydata = SplineData.P12.SA0.IA0.(FxVar).*4.448;
 
 
Xb = lsqcurvefit(Base.F_x,x0b,kappa,ydata,lbb,ubb,opts);

for n = 1:length(Xb)
    BaseList{n,4} = Xb(n);
    BaseList{n,5} = lbb(n);
    BaseList{n,6} = ubb(n);
end
Rawdata_Xvar = RawData.P12.SA0.IA0.(strcat('SL_','R',string(Round),'_Rn',string(Run),'_',string(Fz_nom),'FZ_',string(P),'P_0IA'));
Rawdata_Yvar = RawData.P12.SA0.IA0.(strcat('FX_','R',string(Round),'_Rn',string(Run),'_',string(Fz_nom),'FZ_',string(P),'P_0IA'));


BaseList  = cell2table(BaseList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});     
yfit.Fz150 = feval(Base.F_x ,Xb,kappa);
OutFig.Tabs.Base.Pure= uitab(OutFig.TabGroup.Pure,'Title','Base');
OutFig.Axes.Base.Pure = axes(OutFig.Tabs.Base.Pure);
hold(OutFig.Axes.Base.Pure,'on')
plot(OutFig.Axes.Base.Pure,Rawdata_Xvar,Rawdata_Yvar*4.448,'.k','MarkerSize',10)
plot(OutFig.Axes.Base.Pure,kappa,ydata,'r','LineWidth',3)
plot(OutFig.Axes.Base.Pure,kappa,yfit.Fz150,'Color',[0.75,0.75,0.75],'LineWidth',2)
grid(OutFig.Axes.Base.Pure,'on')
title(OutFig.Axes.Base.Pure,'Base Fit')
legend(OutFig.Axes.Base.Pure,'Raw','Spline','Pacejka','Location','best')

figure;
plot(kappa, ydata - Base.F_x(Xb, kappa), 'ro');
grid on
title('Residuals of Fit');
xlabel('Slip Ratio');
ylabel('Residual (Raw - Fit)');

%% Finding of Terms including dFz
 ubfz = [ 0,  0.5, 0,   0,   0.5,  0.001,  0]';
 lbfz = [-50, 0,   0,  -30,  0,   -0.001, -1]';
m=0; 
for n = 1:length(Fz_vals)
     if Fz_vals(n) == Fz_nom
         disp(['Fz_vals(n): ', num2str(Fz_vals(n)), ', Fz_nom: ', num2str(Fz_nom)]);
         
         disp(strcat('Starting fit for ',string(Fz_vals(n))));
         m = m+1;
         Fz  = Fz_vals(n).*4.448;
         dfz = (Fz-Fz_0_prime)./Fz_0_prime;
        
         dFzFit.S_Hx    = @(Xf)   Xb(6) + Xf(6).*dfz  ;    % Horizontal Offset
         dFzFit.mu_x    = @(Xf)   Xb(2) + Xf(1).*dfz;     % Base Mu value
         dFzFit.kappa_x = @(Xf) kappa+ dFzFit.S_Hx(Xf);
         dFzFit.C_x     = @(Xf) Xb(1);
         dFzFit.D_x     = @(Xf) dFzFit.mu_x(Xf).*Fz.*Zeta.z1;
         dFzFit.E_x     = @(Xf) (Xb(3) + Xf(2).*dfz + (Xf(3).*(dfz.^2)))*(1-Xb(4).*sign(kappa));
         dFzFit.K_x     = @(Xf) Fz.*(Xb(5)+Xf(4).*dfz).*exp(Xf(5).*dfz);
         dFzFit.B_x     = @(Xf) dFzFit.K_x(Xf)./(dFzFit.C_x(Xf).*dFzFit.D_x(Xf)+epsilon.x);
         dFzFit.S_Vx    = @(Xf) Fz.*(Xb(7)+Xf(7).*dfz);
 
         dFzFit.F_x     = @(Xf,kappa) dFzFit.D_x(Xf).*sin(dFzFit.C_x(Xf).*atan(dFzFit.B_x(Xf).*dFzFit.kappa_x(Xf) -dFzFit.E_x(Xf).*(dFzFit.B_x(Xf).*dFzFit.kappa_x(Xf)-atan(dFzFit.B_x(Xf).*dFzFit.kappa_x(Xf))))) + dFzFit.S_Vx(Xf);
           
        
         FxVar = strcat('FX_',TestID,'_',string(Fz_vals(n)),'FZ_12P_0IA');
         ydata = SplineData.P12.SA0.IA0.(FxVar).*4.448;
          
         Xf_out(:,m) = lsqcurvefit(dFzFit.F_x,x0fz,kappa,ydata,lbfz,ubfz,opts);
 
         disp(strcat('Fit for',string(Fz_vals(n)),'complete'))
         yfit.(strcat('FZ',string(Fz_vals(n)))) = feval(dFzFit.F_x,Xf_out(:,m),kappa);
          
         
         OutFig.Tabs.dfz.Pure = uitab(OutFig.TabGroup.Pure,'Title','dFz');
         OutFig.Axes.dfZ      =  axes(OutFig.Tabs.dfz.Pure);
         hold(OutFig.Axes.dfZ,'on')
         plot(OutFig.Axes.dfZ,kappa,ydata,'LineWidth',1.5)
         plot(OutFig.Axes.dfZ,kappa,yfit.(strcat('FZ',string(Fz_vals(n)))),'LineWidth',1.5);
         title(OutFig.Axes.dfZ,string(Fz_vals(n)))
         grid(OutFig.Axes.dfZ,'on')
         legend(OutFig.Axes.dfZ,'Spline','Pacejika','Location','best')
     end
end  
 
for n = 1:length(Xf_out)
    FzList{n,4} = Xf_out(n);
    FzList{n,5} = lbfz(n);
    FzList{n,6} = ubfz(n);
end 
FzList  = cell2table(FzList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});     

%% dPi Parameters

for n = 1:length(x0dPi)
    dPiList{n,4} = 0;
    dPiList{n,5} = 0;
    dPiList{n,6} = 0;
end

%% Finding of terms including gamma
ubIA = [300];
lbIA = [0];
% kappa =(FitData_IA_2.SL_Fit);
Fz_vals = [150];



% Finds coeffecients
for n = 1:length(Fz_vals)
        disp(strcat('Starting fit for ',string(Fz_vals(n))));
        Fz  = Fz_vals(n).*4.448;
        dfz = (Fz-Fz_0_prime)./Fz_0_prime;
        dIAFit.S_Hx    = @(XIA)   Xb(6) + Xf_out(6).*dfz  ;    % Horizontal Offset
        dIAFit.mu_x    = @(XIA)   (Xb(2) + Xf_out(1).*dfz).*(1-XIA(1).*(gamma^2)) ;     % Base Mu value
        dIAFit.kappa_x = @(XIA) kappa+ dIAFit.S_Hx(XIA);
        dIAFit.C_x     = @(XIA) Xb(1);
        dIAFit.D_x     = @(XIA) dIAFit.mu_x(XIA).*Fz.*Zeta.z1;
        dIAFit.E_x     = @(XIA) (Xb(3) + Xf_out(2).*dfz + (Xf_out(3).*(dfz.^2))).*(1-Xb(4).*sign(kappa));
        dIAFit.K_x     = @(XIA) Fz.*(Xb(5)+Xf_out(4).*dfz).*exp(Xf_out(5).*dfz);
        dIAFit.B_x     = @(XIA) dIAFit.K_x(XIA)./(dIAFit.C_x(XIA).*dIAFit.D_x(XIA)+epsilon.x);
        dIAFit.S_Vx    = @(XIA) Fz.*(Xb(7)+Xf_out(7).*dfz);
 
        dIAFit.F_x     = @(XIA,kappa) dIAFit.D_x(XIA).*sin(dIAFit.C_x(XIA).*atan(dIAFit.B_x(XIA).*dIAFit.kappa_x(XIA) -dIAFit.E_x(XIA).*(dIAFit.B_x(XIA).*dIAFit.kappa_x(XIA)-atan(dIAFit.B_x(XIA).*dIAFit.kappa_x(XIA))))) + dIAFit.S_Vx(XIA);
        
        FxVar =strcat('FX_R',string(Round),'_Rn',string(Run),'_150FZ_12P_2IA');
        ydata = SplineData.P12.SA0.IA2.(FxVar);
         
        XIA_out(:,n) = lsqcurvefit(dIAFit.F_x,x0IA,kappa,ydata,lbIA,ubIA,opts);
        
        yfit.IA2.(strcat('FZ',string(Fz_vals(n)))) = feval(dIAFit.F_x,XIA_out(:,n),kappa); % Evaluates Pacejka model with coeffecients
        
        
%       Creates tabs and plots for output
        OutFig.Tab.dIA.Pure = uitab(OutFig.TabGroup.Pure,'Title','dIA');
        OutFig.Axes.dIA.Pure = axes(OutFig.Tab.dIA.Pure);
        hold( OutFig.Axes.dIA.Pure,'on')
        plot(OutFig.Axes.dIA.Pure,kappa,ydata,'LineWidth',1.5);
        plot(OutFig.Axes.dIA.Pure,kappa,yfit.IA2.(strcat('FZ',string(Fz_vals(n)))),'LineWidth',1.5);
        grid(OutFig.Axes.dIA.Pure,'on')
 
        legend(OutFig.Axes.dIA.Pure,'Spline','Pacejka','Location','best')
end
 
for n = 1:length(XIA_out)
    IAList{n,4} = XIA_out(n);
    IAList{n,5} = lbIA(n);
    IAList{n,6} = ubIA(n);
end 
IAList  = cell2table(IAList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});     


%% Combined Slip Fitting (Base)

ubcb = [  15, 18, 1,   0,     0.001];
lbcb = [  8,  10, 0,   -0.95, -0.001];
for n = 1:length(SA_vals)  
    alpha_star = SA_vals(n).*pi./180;
    Fz  = 150.*4.448;
    dfz = (Fz-Fz_0_prime)./Fz_0_prime;
    
    CBaseFit.F_x = feval(Base.F_x,Xb,kappa);
     
    CBaseFit.B_xa	 = @(Xcb) Xcb(1).*cos(atan(Xcb(2).*kappa));
    CBaseFit.C_xa  	 = @(Xcb) Xcb(3);
    CBaseFIt.E_xa    = @(Xcb) Xcb(4);
    CBaseFit.S_Hxa   = @(Xcb) Xcb(5);
    CBaseFit.Alpha_S = @(Xcb) alpha_star + CBaseFit.S_Hxa(Xcb);
    
    CBaseFit.G_xao   = @(Xcb) cos(CBaseFit.C_xa(Xcb).*atan(CBaseFit.B_xa(Xcb).*CBaseFit.S_Hxa(Xcb)-CBaseFIt.E_xa(Xcb).*(CBaseFit.B_xa(Xcb).*CBaseFit.S_Hxa(Xcb)-atan(CBaseFit.B_xa(Xcb).*CBaseFit.S_Hxa(Xcb)))));
    CBaseFit.G_xa    = @(Xcb) cos(CBaseFit.C_xa(Xcb).*atan(CBaseFit.B_xa(Xcb).*CBaseFit.Alpha_S(Xcb)-CBaseFIt.E_xa(Xcb).*(CBaseFit.B_xa(Xcb).*CBaseFit.Alpha_S(Xcb)-atan(CBaseFit.B_xa(Xcb).*CBaseFit.Alpha_S(Xcb)))))./CBaseFit.G_xao(Xcb);
    CBaseFit.F_xc    = @(Xcb,kappa) CBaseFit.G_xa(Xcb).*CBaseFit.F_x;
    
    FxVar = strcat('FX_',TestID,'_',string(Fz_nom),'FZ_',string(P),'P_','0IA');
    ydata = SplineData.P12.(strcat('SA',string(abs(SA_vals(n))))).IA0.FX_R9_Rn72_150FZ_12P_0IA;
    Xcb_out = lsqcurvefit(CBaseFit.F_xc,xc0b,kappa,ydata,lbcb,ubcb,opts);

    yfit.Combined.Base = feval(CBaseFit.F_xc,Xcb_out,kappa);
    figure(2)
    OutFig.Tab.Base.Comb = uitab(OutFig.TabGroup.Comb,'Title','Base');
    OutFig.Axes.Base.Comb = axes(OutFig.Tab.Base.Comb);
    hold on
    plot(OutFig.Axes.Base.Comb,kappa,ydata,'LineWidth',1.5)
    plot(OutFig.Axes.Base.Comb,kappa,yfit.Combined.Base,'LineWidth',1.5);
    legend('Spline','Pacejka','Location','best');
    grid on
    title('Base Fit')
end   

for n = 1:length(Xcb_out)
    CombBaseList{n,4} = Xcb_out(n);
    CombBaseList{n,5} = lbcb(n);
    CombBaseList{n,6} = ubcb(n);
end

CombBaseList  = cell2table(CombBaseList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});     
%% Combined Slip (dFz)
    ubcfz = [ 20];
    lbcfz = [-10];
    Fz_vals = 200;
         alpha_star = SA_vals.*pi./180;
         Fz  = Fz_vals.*4.448;
         dfz = (Fz-Fz_0_prime)./Fz_0_prime;
         Xf = Xf_out;
         dFzFit.S_Hx    =   Xb(6) + Xf(6).*dfz  ;    % Horizontal Offset
         dFzFit.mu_x    =  Xb(2) + Xf(1).*dfz;     % Base Mu value
         dFzFit.kappa_x =  kappa+ dFzFit.S_Hx ;
         dFzFit.C_x     =  Xb(1);
         dFzFit.D_x     =  dFzFit.mu_x.*Fz.*Zeta.z1;
         dFzFit.E_x     =  (Xb(3) + Xf(2).*dfz + (Xf(3).*(dfz.^2))).*(1-Xb(4).*sign(kappa));
         dFzFit.K_x     = Fz.*(Xb(5)+Xf(4).*dfz).*exp(Xf(5).*dfz);
         dFzFit.B_x     =  dFzFit.K_x ./(dFzFit.C_x .*dFzFit.D_x +epsilon.x);
         dFzFit.S_Vx    =  Fz.*(Xb(7)+Xf(7).*dfz);
 
         dFzFit.F_x     =  dFzFit.D_x .*sin(dFzFit.C_x .*atan(dFzFit.B_x .*dFzFit.kappa_x  -dFzFit.E_x .*(dFzFit.B_x .*dFzFit.kappa_x -atan(dFzFit.B_x .*dFzFit.kappa_x )))) + dFzFit.S_Vx;
         
         
      
         CdFzFit.B_xa	 = @(XcdFz) Xcb_out(1).*cos(atan(Xcb_out(2).*kappa));
         CdFzFit.C_xa    = @(XcdFz) Xcb_out(3);
         CdFzFit.E_xa    = @(XcdFz) Xcb_out(4) + XcdFz(1).*dfz;
         CdFzFit.S_Hxa   = @(XcdFz) Xcb_out(5);
         CdFzFit.Alpha_S = @(XcdFz) alpha_star + CdFzFit.S_Hxa(XcdFz);
         
         CdFzFit.G_xao   = @(XcdFz) cos(CdFzFit.C_xa(XcdFz).*atan(CdFzFit.B_xa(XcdFz).*CdFzFit.S_Hxa(XcdFz)-CdFzFit.E_xa(XcdFz).*(CdFzFit.B_xa(XcdFz).*CdFzFit.S_Hxa(XcdFz)-atan(CdFzFit.B_xa(XcdFz).*CdFzFit.S_Hxa(XcdFz)))));
         CdFzFit.G_xa    = @(XcdFz) cos(CdFzFit.C_xa(XcdFz).*atan(CdFzFit.B_xa(XcdFz).*CdFzFit.Alpha_S(XcdFz)-CdFzFit.E_xa(XcdFz).*(CdFzFit.B_xa(XcdFz).*CdFzFit.Alpha_S(XcdFz)-atan(CdFzFit.B_xa(XcdFz).*CdFzFit.Alpha_S(XcdFz)))))./CdFzFit.G_xao(XcdFz);
         CdFzFit.F_xc    = @(XcdFz,kappa) CdFzFit.G_xa(XcdFz).*dFzFit.F_x;
            
         FxVar = strcat('FX_',TestID,'_',string(Fz_vals),'FZ_',string(P),'P_','0IA');
         ydata = SplineData.P12.(strcat('SA',string(abs(SA_vals)))).IA0.(FxVar).*4.448;
         
         XcdFz_out = lsqcurvefit(CdFzFit.F_xc,xc0fz,kappa,ydata,lbcfz,ubcfz,opts);
         
         yfit.Combined.dFz = feval(CdFzFit.F_xc,XcdFz_out,kappa);
         
         figure(2)
         OutFig.Tab.dFz.Comb = uitab(OutFig.TabGroup.Comb,'Title','dFz');
         OutFig.Axes.dFz.Comb = axes(OutFig.Tab.dFz.Comb);
         hold on
         plot(kappa,ydata,'LineWidth',1.5)
         plot(kappa,yfit.Combined.dFz,'LineWidth',1.5);
         legend('Spline','Pacejka','Location','best');
         grid on
         title('dFz Fit')
         
         for n = 1:length(XcdFz_out)
             CombFzList{n,4} = XcdFz_out(n);
             CombFzList{n,5} = lbcfz(n);
             CombFzList{n,6} = ubcfz(n);
         end
CombFzList  = cell2table(CombFzList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});              

%% Combined Including Gamma
    ubcIA = [500];
    lbcIA = [200];
    Fz =  Fz_0_prime;
    dfz = (Fz-Fz_0_prime)./Fz_0_prime;
    Xf = Xf_out;
     dIAFit.S_Hx    = @(XIA)   Xb(6) + Xf_out(6).*dfz  ;    % Horizontal Offset
     dIAFit.mu_x    = @(XIA)   (Xb(2) + Xf_out(1).*dfz).*(1-XIA(1).*(gamma^2)) ;     % Base Mu value
     dIAFit.kappa_x = @(XIA) kappa+ dIAFit.S_Hx(XIA);
     dIAFit.C_x     = @(XIA) Xb(1);
     dIAFit.D_x     = @(XIA) dIAFit.mu_x(XIA).*Fz.*Zeta.z1;
     dIAFit.E_x     = @(XIA) (Xb(3) + Xf_out(2).*dfz + (Xf_out(3).*(dfz.^2))).*(1-Xb(4).*sign(kappa));
     dIAFit.K_x     = @(XIA) Fz.*(Xb(5)+Xf_out(4).*dfz).*exp(Xf_out(5).*dfz);
     dIAFit.B_x     = @(XIA) dIAFit.K_x(XIA)./(dIAFit.C_x(XIA).*dIAFit.D_x(XIA)+epsilon.x);
     dIAFit.S_Vx    = @(XIA) Fz.*(Xb(7)+Xf_out(7).*dfz);
 
     dIAFit.F_x     = @(XIA,kappa) dIAFit.D_x(XIA).*sin(dIAFit.C_x(XIA).*atan(dIAFit.B_x(XIA).*dIAFit.kappa_x(XIA) -dIAFit.E_x(XIA).*(dIAFit.B_x(XIA).*dIAFit.kappa_x(XIA)-atan(dIAFit.B_x(XIA).*dIAFit.kappa_x(XIA))))) + dIAFit.S_Vx(XIA);

    CdIAFit.F_x = feval(dIAFit.F_x,XIA_out,kappa);
   
    CdIAFit.B_xa	= @(XcdIA) (Xcb_out(1)+(XcdIA(1).*(gamma.^2))).*cos(atan(Xcb_out(2).*kappa));
    CdIAFit.C_xa    = @(XcdIA) Xcb_out(3);
    CdIAFit.E_xa    = @(XcdIA) Xcb_out(4) + XcdFz_out(1).*dfz;
    CdIAFit.S_Hxa   = @(XcdIA) Xcb_out(5);
    CdIAFit.Alpha_S = @(XcdIA) alpha_star + CdIAFit.S_Hxa(XcdIA);
    
    CdIAFit.G_xao   = @(XcdIA) cos(CdIAFit.C_xa(XcdIA).*atan(CdIAFit.B_xa(XcdIA).*CdIAFit.S_Hxa(XcdIA)-CdIAFit.E_xa(XcdIA).*(CdIAFit.B_xa(XcdIA).*CdIAFit.S_Hxa(XcdIA)-atan(CdIAFit.B_xa(XcdIA).*CdIAFit.S_Hxa(XcdIA)))));
    CdIAFit.G_xa    = @(XcdIA) cos(CdIAFit.C_xa(XcdIA).*atan(CdIAFit.B_xa(XcdIA).*CdIAFit.Alpha_S(XcdIA)-CdIAFit.E_xa(XcdIA).*(CdIAFit.B_xa(XcdIA).*CdIAFit.Alpha_S(XcdIA)-atan(CdIAFit.B_xa(XcdIA).*CdIAFit.Alpha_S(XcdIA)))))./CdIAFit.G_xao(XcdIA);
    CdIAFit.F_xc    = @(XcdIA,kappa) CdIAFit.G_xa(XcdIA).*CdIAFit.F_x;
    
    FxVar = strcat('FX_',TestID,'_',string(Fz_nom),'FZ_',string(P),'P_','2IA');
    ydata = SplineData.P12.(strcat('SA',string(abs(SA_vals)))).IA2.(FxVar).*4.448;
    
    XcdIA_out = lsqcurvefit(CdIAFit.F_xc,xc0IA,kappa,ydata,lbcIA,ubcIA,opts);
    
    yfit.Combined.dIA = feval(CdIAFit.F_xc,XcdIA_out,kappa);

    
    figure(2)
    OutFig.Tab.dIA.Comb = uitab(OutFig.TabGroup.Comb,'Title','dIA');
    OutFig.Axes.dIA.Comb = axes(OutFig.Tab.dIA.Comb);
    hold on
    plot(kappa,ydata,'LineWidth',1.5)
    plot(kappa,yfit.Combined.dIA,'LineWidth',1.5);
    legend('Spline','Pacejka','Location','best');
    grid on
    title('dFz Fit')
    
    for n = 1:length(XcdIA_out)
        CombIAList{n,4} = XcdIA_out(n);
        CombIAList{n,5} = lbcIA(n);
        CombIAList{n,6} = ubcIA(n);
    end
CombIAList  = cell2table(CombIAList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});                  
%% Combined Lateral Slip Base Terms
     ubcFyb =  [ 25,  10,  50  50, 50,  50,  50,  2,  2,  50];
     lbcFyb =  [0, -10, -50, -50, -50, -50, -50, -50, -50, -50];
   
     Fz = Fz_0_prime;
    [Fy0, mu_y] = Pacejka_FY(Fz,Fz_0_prime,0,alpha_star);
    
    CyBaseFit.B_yk  = @(Ycb) (Ycb(1)).*cos(atan(Ycb(2).*(alpha_star-Ycb(3))));
    CyBaseFit.C_yk  = @(Ycb)  Ycb(4);
    CyBaseFit.D_yk  = @(Ycb)  mu_y.*Fz.*(Ycb(7)).*cos(atan(Ycb(8).*alpha_star));
    CyBaseFit.E_yk  = @(Ycb)  Ycb(5);
    CyBaseFit.S_Hyk = @(Ycb)  Ycb(6);
    CyBaseFit.S_Vyk = @(Ycb)  CyBaseFit.D_yk(Ycb).*sin(Ycb(9).*atan(Ycb(10).*kappa));
    CyBaseFit.K_s   = @(Ycb)  kappa + CyBaseFit.S_Hyk(Ycb);
    CyBaseFit.G_yko = @(Ycb) cos(CyBaseFit.C_yk(Ycb).*atan(CyBaseFit.B_yk(Ycb).*CyBaseFit.S_Hyk(Ycb) - CyBaseFit.E_yk(Ycb).*(CyBaseFit.B_yk(Ycb).*CyBaseFit.S_Hyk(Ycb)- atan(CyBaseFit.B_yk(Ycb).*CyBaseFit.S_Hyk(Ycb)))));
    CyBaseFit.G_yk  = @(Ycb) cos(CyBaseFit.C_yk(Ycb).*atan(CyBaseFit.B_yk(Ycb).*CyBaseFit.K_s(Ycb) - CyBaseFit.E_yk(Ycb).*(CyBaseFit.B_yk(Ycb).*CyBaseFit.K_s(Ycb)- atan(CyBaseFit.B_yk(Ycb).*CyBaseFit.K_s(Ycb)))))./CyBaseFit.G_yko(Ycb);
    CyBaseFit.Fyc   = @(Ycb,kappa) Fy0.*CyBaseFit.G_yk(Ycb)+CyBaseFit.S_Vyk(Ycb);
    
    FyVar = strcat('FY_',TestID,'_',string(Fz_nom),'FZ_',string(P),'P_','0IA');
    ydata = SplineData.P12.(strcat('SA',string(abs(SA_vals)))).IA0.(FyVar).*4.448;
     
    Ycb = lsqcurvefit( CyBaseFit.Fyc,yc0b,kappa,ydata,lbcFyb,ubcFyb,opts);
    yfit.Combined.FyBase = feval(CyBaseFit.Fyc,Ycb,kappa);
     
    for n = 1:length(Ycb)
        FyBaseList{n,4} = Ycb(n);
        FyBaseList{n,5} = lbcFyb(n);
        FyBaseList{n,6} = ubcFyb(n);
    end
    
    figure(2)
    OutFig.Tab.FyBase.Comb = uitab(OutFig.TabGroup.Comb,'Title','Fy base');
    OutFig.Axes.FyBase.Comb = axes(OutFig.Tab.FyBase.Comb);
    hold on
    plot(kappa,ydata,'LineWidth',1.5)
    plot(kappa,yfit.Combined.FyBase,'LineWidth',1.5);
    legend('Spline','Pacejka','Location','best');
    grid on
    title('Fy Base Fit')

FyBaseList  = cell2table(FyBaseList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});                  

%% Combined Lateral Slip dFz Terms
     ubcFyFz = [ 5,  0.01, 1];
     lbcFyFz = [-5, -0.01,-1];    
    
     Fz = Fz_vals.*4.448;
     dfz = (Fz-Fz_0_prime)./Fz_0_prime;
    [Fy0, mu_y] = Pacejka_FY(Fz,Fz_0_prime,0,alpha_star);
     
    CydFzFit.B_yk  = @(Ycfz ) (Ycb(1)).*cos(atan(Ycb(2).*(alpha_star-Ycb(3))));
    CydFzFit.C_yk  = @(Ycfz)  Ycb(4);
    CydFzFit.D_yk  = @(Ycfz)  mu_y.*Fz.*(Ycb(7) +  Ycfz(3).*dfz).*cos(atan(Ycb(8).*alpha_star));
    CydFzFit.E_yk  = @(Ycfz)  Ycb(5) + Ycfz(1).*dfz;
    CydFzFit.S_Hyk = @(Ycfz)  Ycb(6) + Ycfz(2).*dfz;
    CydFzFit.S_Vyk = @(Ycfz)  CydFzFit.D_yk(Ycfz).*sin(Ycb(9).*atan(Ycb(10).*kappa));
    CydFzFit.K_s   = @(Ycfz)  kappa + CydFzFit.S_Hyk(Ycfz);
    CydFzFit.G_yko = @(Ycfz) cos(CydFzFit.C_yk(Ycfz).*atan(CydFzFit.B_yk(Ycfz).*CydFzFit.S_Hyk(Ycfz) - CydFzFit.E_yk(Ycfz).*(CydFzFit.B_yk(Ycfz).*CydFzFit.S_Hyk(Ycfz)- atan(CydFzFit.B_yk(Ycfz).*CydFzFit.S_Hyk(Ycfz)))));
    CydFzFit.G_yk  = @(Ycfz) cos(CydFzFit.C_yk(Ycfz).*atan(CydFzFit.B_yk(Ycfz).*CydFzFit.K_s(Ycfz) - CydFzFit.E_yk(Ycfz).*(CydFzFit.B_yk(Ycfz).*CydFzFit.K_s(Ycfz)- atan(CydFzFit.B_yk(Ycfz).*CydFzFit.K_s(Ycfz)))))./CydFzFit.G_yko(Ycfz);
    CydFzFit.Fyc   = @(Ycfz,kappa) Fy0.*CydFzFit.G_yk(Ycfz)+CydFzFit.S_Vyk(Ycfz);   

    FyVar = strcat('FY_',TestID,'_',string(Fz_vals),'FZ_',string(P),'P_','0IA');
    ydata = SplineData.P12.(strcat('SA',string(abs(SA_vals)))).IA0.(FyVar).*4.448;
     
    Ycfz = lsqcurvefit(CydFzFit.Fyc,yc0fz,kappa,ydata,lbcFyFz,ubcFyFz,opts);
    yfit.Combined.FydFz = feval(CydFzFit.Fyc,Ycfz,kappa);
    
    figure(2)
    OutFig.Tab.FydFz.Comb = uitab(OutFig.TabGroup.Comb,'Title','Fy dFz');
    OutFig.Axes.FydFz.Comb = axes(OutFig.Tab.FydFz.Comb);
    hold on
    plot(kappa,ydata,'LineWidth',1.5)
    plot(kappa,yfit.Combined.FydFz,'LineWidth',1.5);
    legend('Spline','Pacejka','Location','best');
    grid on
    title('Fy dFz Fit')
    for n = 1:length(Ycfz)
        FyFzList{n,4} = Ycfz(n);
        FyFzList{n,5} = lbcFyFz(n);
        FyFzList{n,6} = ubcFyFz(n);
    end
FyFzList  = cell2table(FyFzList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});         

%% Combined Lateral Slip dIA Terms   
     ubcFyIA = [ 500, 50];
     lbcFyIA = [-2000, -50];
     
     Fz = Fz_0_prime;
    [Fy0, mu_y] = Pacejka_FY(Fz,Fz_0_prime,gamma,alpha_star); 
    
     CyIAFit.B_yk  = @(YcIA)       (Ycb(1)+YcIA(1).*(gamma.^2)).*cos(atan(Ycb(2).*(alpha_star-Ycb(3))));
     CyIAFit.C_yk  = @(YcIA)       Ycb(4);
     CyIAFit.D_yk  = @(YcIA)       mu_y.*Fz.*(Ycb(7)+YcIA(2).*gamma).*cos(atan(Ycb(8).*alpha_star));
     CyIAFit.E_yk  = @(YcIA)       Ycb(5);
     CyIAFit.S_Hyk = @(YcIA)       Ycb(6);
     CyIAFit.S_Vyk = @(YcIA)       CyIAFit.D_yk(YcIA).*sin(Ycb(9).*atan(Ycb(10).*kappa));
     CyIAFit.K_s   = @(YcIA)       kappa + CyIAFit.S_Hyk(YcIA);
     CyIAFit.G_yko = @(YcIA)       cos(CyIAFit.C_yk(YcIA).*atan(CyIAFit.B_yk(YcIA).*CyIAFit.S_Hyk(YcIA) - CyIAFit.E_yk(YcIA).*(CyIAFit.B_yk(YcIA).*CyIAFit.S_Hyk(YcIA)- atan(CyIAFit.B_yk(YcIA).*CyIAFit.S_Hyk(YcIA)))));
     CyIAFit.G_yk  = @(YcIA)       cos(CyIAFit.C_yk(YcIA).*atan(CyIAFit.B_yk(YcIA).*CyIAFit.K_s(YcIA) - CyIAFit.E_yk(YcIA).*(CyIAFit.B_yk(YcIA).*CyIAFit.K_s(YcIA)- atan(CyIAFit.B_yk(YcIA).*CyIAFit.K_s(YcIA)))))./CyIAFit.G_yko(YcIA);
     CyIAFit.Fyc   = @(YcIA,kappa) Fy0.*CyIAFit.G_yk(YcIA)+CyIAFit.S_Vyk(YcIA);
    
     FyVar = strcat('FY_',TestID,'_',string(Fz_nom),'FZ_',string(P),'P_',string(gamma_vals),'IA');
     ydata = SplineData.P12.(strcat('SA',string(abs(SA_vals)))).(strcat('IA',string(gamma_vals))).(FyVar).*4.448;     
     YcIA = lsqcurvefit( CyIAFit.Fyc,yc0IA,kappa,ydata,lbcFyIA,ubcFyIA,opts);
     yfit.Combined.FYdIA = feval(CyIAFit.Fyc,YcIA,kappa);
     
     
    figure(2)
    OutFig.Tab.FydIA.Comb = uitab(OutFig.TabGroup.Comb,'Title','Fy dIA');
    OutFig.Axes.FydIA.Comb = axes(OutFig.Tab.FydIA.Comb);
    hold on
    plot(kappa,ydata,'LineWidth',1.5)
    plot(kappa,yfit.Combined.FYdIA,'LineWidth',1.5);
    legend('Spline','Pacejka','Location','best');
    grid on
    title('FY dIA Fit')
     
    for n = 1:length(YcIA)
        FyIAList{n,4} = YcIA(n);
        FyIAList{n,5} = lbcFyIA(n);
        FyIAList{n,6} = ubcFyIA(n);
    end
    
FYIAList  = cell2table(FyIAList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});

%% Gathering Parameters and Exporting Them to .mat File
FX_ParameterList = [BaseList ;FzList;dPiList;IAList; CombBaseList; CombFzList;CombIAList;FyBaseList;FyFzList;FyIAList];
    
FileName = strcat('FX_Parameters','_',Tire,'_',string(Round),'_', string(Fz_nom), 'FZ',string(Run),'.mat');
save(strcat("CC's tire model folder\Fitted Parameters\",FileName),'FX_ParameterList')   

function [Fyo, mu_y] = Pacejka_FY(Fz,Fz0_prime,gamma_star,alpha_star)
FYFileName = strcat('FY_Parameters','_',Tire,'_',string(Round),'_33_',string(Fz_nom),'FZ','.mat');
data = load (strcat("CC's tire model folder\Fitted Parameters\", FYFileName));
assignin('base', 'FY_ParameterList', data.FY_ParameterList)
    
p = struct();
for n = 1:height(data.FY_ParameterList)
p.(data.FY_ParameterList.Variable{n,1}) = data.FY_ParameterList.Final(n,1);
orderfields(p);
end

dpi = 0; 
dfz = (Fz-Fz0_prime)/Fz0_prime;
epsilon.y = 0.1;
epsilon.k = 0.1;


K_yalpha   = p.Ky1.*Fz0_prime.*(1+p.py1.*dpi).*(1-p.Ky3.*abs(gamma_star)).*sin(p.Ky4.*atan((Fz./Fz0_prime)./((p.Ky2+p.Ky5.*gamma_star.^2).*(1+p.py2.*dpi)))); 
S.Vy_gamma = Fz.*(p.Vsy3 + p.Vsy4.*dfz).*gamma_star;
K_ygo      = Fz.*(p.Ky6 + p.Ky7.*dfz);
S.Hy       = (p.Hsy1 +p.Hsy2.*dfz) + (K_ygo.*gamma_star-S.Vy_gamma)./(K_yalpha+epsilon.k);
alpha_y    = alpha_star+S.Hy;
Cy         = p.Cy1; 
mu_y       = (p.Dy1+p.Dy2.*dfz).*(1+p.py3.*dpi+p.py4.*(dpi.^2)).*(1-p.Dy3.*(gamma_star.^2));
Dy         = mu_y.*Fz;
Ey         = (p.Ey1+p.Ey2.*dfz).*(1+p.Ey5.*gamma_star.^2-(p.Ey3+p.Ey4.*gamma_star).*sign(alpha_star));
By         = K_yalpha./(Cy.*Dy+epsilon.y);
% Hy         = (p.Hy1 + p.Hy2.*dfz);
S.Vy       = Fz.*(p.Vsy1 + p.Vsy2.*dfz) +S.Vy_gamma;
Fyo        = Dy.*sin(Cy.*atan(By.*alpha_y-Ey.*(By.*alpha_y-atan(By.*alpha_y))))+S.Vy;

end
end