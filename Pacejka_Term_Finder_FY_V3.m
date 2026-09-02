% FY Pacjeka Term Finder V2
% V3 includes combined slip fits

function [FY_ParameterList, yfit, Alpha] = Pacejka_Term_Finder_FY_V3(Round, Run, Tire, Fz_nom)

%% Test Information
TestID = strcat('R',string(Round),'_Rn',string(Run));
Type = 'Fy';
TireMan = 'Michelin';

% Parameter Values
P = 12; %psi
Fz_vals = [50];
gamma_vals = [0]; %deg
 

%% Fit Options
opts = optimset('TolFun',1e-8,'MaxFunEvals',120000,'MaxIter',120000,'TolX',1e-8); %optimization settings
addpath(genpath('FY Data')) % adds directory to file search path
[SplineData] = Raw_Data_Fitter_Fy_V3(Round,Run,Tire); % separate function

%% Fit Data Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

Fz_N   =  Fz_nom .*4.448; %(N) normal load
p_i   = P*82.737;  %(kPa) inflation pressure
gamma = gamma_vals*pi./180; %(rad)

%% Conversions %%%%
Deg2Rad = pi./180;

%% Base Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
V = 25*1.609/3.6; %m/s
Fz_0 = Fz_N; % nominal wheel load
pio = 12*82.737;  %(kPa) nominal inflation pressure
rl = 8.67*0.0254; %(m) loaded tire radius

Alpha = eval(strcat('SplineData.P12.SA0.IA0.SA_', TestID, '_', string(Fz_nom), 'FZ_12P_0IA')).*Deg2Rad;

Vsx = 0; % components of slip velocity
Vox = V; % sets forward velocity

%% User Scaling Factors - to adjust pacejka model parameters
Lam.Cx = 1;     % shape factor
Lam.mu_x = 1;   % peak friction coeff
Lam.mu_x_star = Lam.mu_x.*(1+Vsx/Vox);
Lam.mu_x_prime = 1;
Lam.Ex =  1;    % curvature factor
Lam.Fz_0 = 1;   % nominal rated load
Lam.Kxk =1;     % brake slip stiffness
Lam.Hx = 1;     % horizontal shift
Lam.Vx = 1;     % vertical shift

%% Constants %%
Fz_0_prime = Lam.Fz_0.*Fz_0; % adapted nominal load
dpi = (p_i-pio)./pio; % normalized Pressure
dfz = (Fz_N-Fz_0_prime)./Fz_0_prime; %normalized FZ

Alpha_star = Alpha;
gamma_star = sin(gamma); % spin due to camber angle

%% Initial Fit Parameters (Pstat = [isBase, is*dFz, is*Ia, is*dPi is*dFz*dIA])
% Pure Lateral Slip Terms
    p0.Cy1  = 0.975;    Pstat.Cy1 = [1 0 0 0 0];
%     p0.Cy2  = 0.24;     Pstat.Cy2 = [1 0 0 0 0];

    p0.Dy1  = 2.625;    Pstat.Dy1 = [1 0 0 0 0];
    p0.Dy2  = -0.01;    Pstat.Dy2 = [0 1 0 0 0];
    p0.Dy3  = 25;       Pstat.Dy3 = [0 0 1 0 0];

    p0.Ey1  = 1.0;      Pstat.Ey1 = [1 0 0 0 0];
    p0.Ey2  =-0.80;     Pstat.Ey2 = [0 1 0 0 0];
    p0.Ey3  = 0;        Pstat.Ey3 = [1 0 0 0 0];
    p0.Ey4  =1;         Pstat.Ey4 = [0 0 1 0 0];
    p0.Ey5  = 1;        Pstat.Ey5 = [0 0 1 0 0];
%     p0.Ey6 = 0.035;     Pstat.Ey6 = [1 0 0 0 0];
    
    p0.Hsy1 = 0;        Pstat.Hsy1 = [1 0 0 0 0];
    p0.Hsy2 = 0;        Pstat.Hsy2 = [0 1 0 0 0];
    
%     p0.Hy1 = -37.5;     Pstat.Hy1 = [1 0 0 0 0];
%     p0.Hy2 = -15;       Pstat.Hy2 = [0 1 0 0 0];

    p0.Ky1  = 175.5;    Pstat.Ky1 = [1 0 0 0 0];
    p0.Ky2  =2.9;       Pstat.Ky2 = [1 0 0 0 0];
    p0.Ky3  = 1;        Pstat.Ky3 = [0 0 1 0 0];
    p0.Ky4  =0.8;       Pstat.Ky4 = [1 0 0 0 0];
    p0.Ky5  = 1;        Pstat.Ky5 = [0 0 1 0 0];
    p0.Ky6  = 3;        Pstat.Ky6 = [0 0 1 0 0];
    p0.Ky7  = 2;        Pstat.Ky7 = [0 0 0 0 1];
    
    p0.py1  = 1;        Pstat.py1 = [0 0 0 1 0];
    p0.py2  = 1;        Pstat.py2 = [0 0 0 1 0];
    p0.py3  = 1;        Pstat.py3 = [0 0 0 1 0];
    p0.py4  = 1;        Pstat.py4 = [0 0 0 1 0];
    p0.py5  = 1;        Pstat.py5 = [0 0 0 1 0];
    
    p0.Vsy1 = 0;        Pstat.Vsy1 = [1 0 0 0 0];         
    p0.Vsy2 = 0;        Pstat.Vsy2 = [0 1 0 0 0];    
    p0.Vsy3 = 3;        Pstat.Vsy3 = [0 0 1 0 0];    
    p0.Vsy4 = 0;        Pstat.Vsy4 = [0 0 0 0 1];    


    epsilon.y = 0.1;
    epsilon.k = 0.1;
    Zeta.z2 = 1;       
    Zeta.z3 = 1;
%% Parameter Lists
 
Pees     =  [repelem({'p0.'},length(fieldnames(p0)),1), fieldnames(p0)];
%Arrs     =  [repelem({'r0.'},length(fieldnames(r0)),1), fieldnames(r0)];
FY_ParameterList = [Pees];%; Arrs];
x0 = zeros(length(FY_ParameterList),1);

for n = 1:length(FY_ParameterList) 
    var = strcat( FY_ParameterList{n,1}, FY_ParameterList{n,2} );
    x0(n,1) = eval(var);
end


%% Output Figure Creation 
% Pure Slip Output Figure %% 
OutFig.Fig.Pure = figure(1);
clf(OutFig.Fig.Pure)
OutFig.Fig.Pure.Name = 'Pure Slip Fitting Results';

OutFig.TabGroup.Pure= uitabgroup(OutFig.Fig.Pure);

% % Combined Slip Output Figure %
% OutFig.Fig.Comb = figure(2);
% clf(OutFig.Fig.Comb )
% OutFig.Fig.Comb.Name = 'Combined Slip Fitting Results';
% OutFig.TabGroup.Comb = uitabgroup(OutFig.Fig.Comb);
 

%% Base Constants For Nominal Load and Zero Inlincation Angle (Negates all terms multiplied by dFz, gamma(IA), or dPi)
m = 0;
q = 0;
j = 0;
k = 0;
r = 0;
s = 0;
t = 0;
p = 0;

for n = 1:length(FY_ParameterList)
    var = FY_ParameterList{n,2}; % gets name of parameter from Pees
    if contains(FY_ParameterList{n,1},'p0.') == 1
        if Pstat.(var)(1) == 1 % base term, independent of Fz, IA, dPi
            m = m +1;
            BaseList{m,1} = 'p.';
            BaseList{m,2} = var;
            BaseList{m,3} = x0(n,1);
            x0b(m,1) = x0(n,1);

        elseif Pstat.(var)(2) == 1 % depends on Fz
             q = q +1;
            FzList{q,1} = 'p.';
            FzList{q,2} = var;
            FzList{q,3} = x0(n,1);
            x0fz(q,1) = x0(n,1);

        elseif Pstat.(var)(3) == 1 % depends on IA
             j = j +1;
            IAList{j,1} = 'p.';
            IAList{j,2} = var;
            IAList{j,3} = x0(n,1);
            x0IA(j,1) = x0(n,1);
            
        elseif Pstat.(var)(4) ==1 % depends on dPi
            p = p+1;
            dPiList{p,1} = 'p.';
            dPiList{p,2} = var;
            dPiList{p,3} = x0(n,1);
            x0dPi(p,1) = x0(n,1);
            
        elseif Pstat.(var)(5) ==1 % depends on both Fz and IA
            k = k+1;
            IAdFzList{k,1} = 'p.';
            IAdFzList{k,2} = var;
            IAdFzList{k,3} = x0(n,1);
            x0IAFz(k,1) = x0(n,1);
        end
        
    % elseif contains(ParameterList{n,1},'r0.') == 1
    %     if Rstat.(var)(1) == 1
    %         r = r +1;
    %         CombBaseList{r,1} = 'r.';
    %         CombBaseList{r,2} = var;
    %         CombBaseList{r,3} = x0(n,1);
    %         xc0b(r,1) = x0(n,1);
    %     elseif Rstat.(var)(2) == 1
    %          s = s +1;
    %         CombFzList{s,1} = 'r.';
    %         CombFzList{s,2} = var;
    %         CombFzList{s,3} = x0(n,1);
    %         xc0fz(s,1) = x0(n,1);
    %     elseif Rstat.(var)(3) == 1
    %          t = t +1;
    %         CombIAList{t,1} = 'r.';
    %         CombIAList{t,2} = var;
    %         CombIAList{t,3} = x0(n,1);
    %         xc0IA(t,1) = x0(n,1);
    %     end
    % end
            
end

%% Base Parameters %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% 
ubb = [1.7, 2.784,  15,  25, 0.001,  -50,  25,  25,  25]';
lbb = [1.5, 2.784, -15, -10, -0.01, -70, -10, -10, -10]';

% Lateral Force shape and scaling
BaseFit.S_Hy    = @(Xb) Xb(5);
BaseFit.mu_y    = @(Xb) Xb(2);
BaseFit.Alpha_y = @(Xb) Alpha_star + BaseFit.S_Hy(Xb);
% MF Parameters
BaseFit.C_y     = @(Xb) Xb(1);
BaseFit.D_y     = @(Xb) BaseFit.mu_y(Xb).*Fz_N;
BaseFit.E_y     = @(Xb) Xb(3).* (1 - Xb(4).*sign(Alpha_star));
% stiffness and b factor
BaseFit.Ky_a    = @(Xb) Xb(6).*Fz_0_prime.*sin(Xb(8).*atan((Fz_N./Fz_0_prime)./(Xb(7))));
BaseFit.B_y     = @(Xb) BaseFit.Ky_a(Xb)./(BaseFit.C_y(Xb).*BaseFit.D_y(Xb) + epsilon.y);
BaseFit.S_Vy    = @(Xb) Fz_N.*(Xb(9));

% Final MF equation
BaseFit.F_yo    = @(Xb,Alpha_Star) BaseFit.D_y(Xb).*sin(BaseFit.C_y(Xb).*atan(BaseFit.B_y(Xb).*BaseFit.Alpha_y(Xb)-BaseFit.E_y(Xb).*(BaseFit.B_y(Xb).*BaseFit.Alpha_y(Xb)-atan(BaseFit.B_y(Xb).*BaseFit.Alpha_y(Xb))))) + BaseFit.S_Vy(Xb);

FyVar = strcat('FY_',TestID,'_',string(Fz_nom),'FZ_12P_0IA');
ydata =SplineData.P12.SA0.IA0.(FyVar).*4.448; % ydata from raw data fitter function

opts_base = optimset('TolFun',1e-8,'MaxFunEvals',400000,'MaxIter',400000,'TolX',1e-8,'FinDiffType','central'); 
Xb = lsqcurvefit(BaseFit.F_yo,x0b,Alpha_star,ydata,lbb,ubb,opts_base);
 
yfit.Base =feval(BaseFit.F_yo ,Xb,Alpha_star);

Check.Base.S_Hy = feval(BaseFit.S_Hy,Xb);
Check.Base.mu_y = feval(BaseFit.mu_y,Xb);
Check.Base.C_y = feval(BaseFit.C_y,Xb);
Check.Base.D_y = feval(BaseFit.D_y,Xb);
Check.Base.E_y = feval(BaseFit.E_y,Xb);
Check.Base.Ky_a = feval(BaseFit.Ky_a,Xb);
Check.Base.B_y = feval(BaseFit.B_y,Xb);
% Check.Base.H_y = feval(BaseFit.H_y,Xb);
Check.Base.S_Vy = feval(BaseFit.S_Vy,Xb);

for n = 1:length(Xb)
    BaseList{n,4} = Xb(n);
    BaseList{n,5} = lbb(n);
    BaseList{n,6} = ubb(n);
end
BaseList  = cell2table(BaseList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});     

OutFig.Tabs.Base.Pure= uitab(OutFig.TabGroup.Pure,'Title','Base');
OutFig.Axes.Base.Pure = axes(OutFig.Tabs.Base.Pure);
hold(OutFig.Axes.Base.Pure,'on')
plot(OutFig.Axes.Base.Pure,Alpha,ydata,'LineWidth',1.5)
plot(OutFig.Axes.Base.Pure,Alpha,yfit.Base,'LineWidth',1.5)
grid(OutFig.Axes.Base.Pure,'on')
xlabel(OutFig.Axes.Base.Pure, 'Slip Angle (rad)')
ylabel(OutFig.Axes.Base.Pure, 'Lateral Force (N)')
title(OutFig.Axes.Base.Pure,'Base Fit')
legend(OutFig.Axes.Base.Pure,'Spline','Pacejka','Location','best')

%% dFz Parameter Fitting %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
ubfz = [ 0.001,  1,  0.01,  10]';
lbfz = [-0.001, -1, -0.01, -10]';

Fz_N  = Fz_vals.*4.448;
dfz = (Fz_N-Fz_0_prime)./max(abs(Fz_0_prime));

dFzFit.S_Hy    = @(Xf) (Xb(5)+Xf(3).*dfz);

dFzFit.mu_y    = @(Xf) (Xb(2)+Xf(1).*dfz);

dFzFit.Alpha_y = @(Xf) Alpha_star + dFzFit.S_Hy(Xf);

dFzFit.C_y     = @(Xf) Xb(1);

dFzFit.D_y     = @(Xf) dFzFit.mu_y(Xf).*Fz_N;

dFzFit.E_y     = @(Xf) (Xb(3)+Xf(2).*dfz).* (1 - Xb(4).*sign(Alpha_star));

dFzFit.Ky_a    = @(Xf) Xb(6).*Fz_0_prime.*sin(Xb(8).*atan((Fz_N./Fz_0_prime)./(Xb(7))));

dFzFit.B_y     = @(Xf) dFzFit.Ky_a(Xf)./(dFzFit.C_y(Xf).*dFzFit.D_y(Xf) + epsilon.y);

dFzFit.S_Vy    = @(Xf) Fz_N.*(Xb(9)+Xf(4).*dfz);

dFzFit.F_yo    = @(Xf,Alpha_Star) dFzFit.D_y(Xf).*sin(dFzFit.C_y(Xf).*atan(dFzFit.B_y(Xf).*dFzFit.Alpha_y(Xf)-dFzFit.E_y(Xf).*(dFzFit.B_y(Xf).*dFzFit.Alpha_y(Xf)-atan(dFzFit.B_y(Xf).*dFzFit.Alpha_y(Xf))))) + dFzFit.S_Vy(Xf);


FyVar = strcat('FY_',TestID,'_',string(Fz_vals),'FZ_12P_0IA');
ydata =SplineData.P12.SA0.IA0.(FyVar);
 
opts = statset('nlinfit');
opts.RobustWgtFun = 'bisquare'; % Suppresses extreme oscillations

Xf = nlinfit(Alpha_star, ydata, dFzFit.F_yo, x0fz, opts);
% Xf = lsqcurvefit(dFzFit.F_yo,x0fz,Alpha_star,ydata,lbfz,ubfz,opts_base);
yfit.dFz =feval(dFzFit.F_yo,Xf,Alpha_star);

Check.dFz.S_Hy = feval(dFzFit.S_Hy,Xf);
Check.dFz.mu_y = feval(dFzFit.mu_y,Xf);
Check.dFz.C_y = feval(dFzFit.C_y,Xf);
Check.dFz.D_y = feval(dFzFit.D_y,Xf);
Check.dFz.E_y = feval(dFzFit.E_y,Xf);
Check.dFz.Ky_a = feval(dFzFit.Ky_a,Xf);
Check.dFz.B_y = feval(dFzFit.B_y,Xf);
% Check.dFz.H_y = feval(dFzFit.H_y,Xf);

for n = 1:length(Xf)
    FzList{n,4} = Xf(n);
    FzList{n,5} = lbfz(n);
    FzList{n,6} = ubfz(n);
end
FzList  = cell2table(FzList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});

OutFig.Tabs.dFz.Pure= uitab(OutFig.TabGroup.Pure,'Title','dFz');
OutFig.Axes.dFz.Pure = axes(OutFig.Tabs.dFz.Pure);
hold(OutFig.Axes.dFz.Pure,'on')
plot(OutFig.Axes.dFz.Pure,Alpha,ydata,'LineWidth',1.5)
plot(OutFig.Axes.dFz.Pure,Alpha,yfit.dFz,'LineWidth',1.5)
grid(OutFig.Axes.dFz.Pure,'on')
title(OutFig.Axes.dFz.Pure,'dFz Fit')
legend(OutFig.Axes.dFz.Pure,'Spline','Pacejka','Location','best')

%% dPi Parameters

for n = 1:length(x0dPi)
    dPiList{n,4} = 0;
    dPiList{n,5} = 0;
    dPiList{n,6} = 0;
end

%% dIA parameters
ubIA = [ 20,  50,  80,  20,  20,  4,  20]; 
lbIA = [-20, -50, 0, -20, -20,  -4, -20];

Fz_N  = Fz_nom.*4.448;

dIA_Fit.Kyg0    = @(XIA) Fz_N.*(XIA(6));

dIA_Fit.SVyg    = @(XIA) Fz_N.*(XIA(7)).*(gamma_star);

dIA_Fit.Ky_a    = @(XIA) Xb(6).*Fz_0_prime.*(1-XIA(4).*abs(gamma_star)).*sin(Xb(8).*atan((Fz_N./Fz_0_prime)./(Xb(7)+(XIA(5).*(gamma_star.^2)))));

dIA_Fit.S_Hy    = @(XIA) Xb(5) + ((dIA_Fit.Kyg0(XIA).*gamma_star - dIA_Fit.SVyg(XIA))./(dIA_Fit.Ky_a(XIA)+epsilon.k));

dIA_Fit.mu_y    = @(XIA) Xb(2).*(1-XIA(1).*(gamma_star.^2));

dIA_Fit.Alpha_y = @(XIA) Alpha_star + dIA_Fit.S_Hy(XIA);

dIA_Fit.C_y     = @(XIA) Xb(1);

dIA_Fit.D_y     = @(XIA) dIA_Fit.mu_y(XIA).*Fz_N;

dIA_Fit.E_y     = @(XIA) Xb(3).* (1 + XIA(3).*(gamma_star.^2) - (Xb(4)+XIA(2).*gamma_star).*sign(Alpha_star));

dIA_Fit.B_y     = @(XIA) dIA_Fit.Ky_a(XIA)./(dIA_Fit.C_y(XIA).*dIA_Fit.D_y(XIA) + epsilon.y);

dIA_Fit.S_Vy    = @(XIA) Fz_N.*(Xb(9)) + dIA_Fit.SVyg(XIA);

dIA_Fit.F_yo    = @(XIA,Alpha_star) dIA_Fit.D_y(XIA).*sin(dIA_Fit.C_y(XIA).*atan(dIA_Fit.B_y(XIA).*dIA_Fit.Alpha_y(XIA)-dIA_Fit.E_y(XIA).*(dIA_Fit.B_y(XIA).*dIA_Fit.Alpha_y(XIA)-atan(dIA_Fit.B_y(XIA).*dIA_Fit.Alpha_y(XIA))))) + dIA_Fit.S_Vy(XIA);

FyVar = strcat('FY_',TestID,'_',string(Fz_nom),'FZ_12P_',string(gamma_vals),'IA');
ydata = SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).(FyVar).*4.448;


XIA = lsqcurvefit(dIA_Fit.F_yo,x0IA,Alpha_star,ydata,lbIA,ubIA,opts_base);
yfit.dIA =feval(dIA_Fit.F_yo,XIA,Alpha_star);

for n = 1:length(XIA)
    IAList{n,4} = XIA(n);
    IAList{n,5} = lbIA(n);
    IAList{n,6} = ubIA(n);
end
IAList  = cell2table(IAList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});

OutFig.Tabs.dIA.Pure= uitab(OutFig.TabGroup.Pure,'Title','dIA');
OutFig.Axes.dIA.Pure = axes(OutFig.Tabs.dIA.Pure);
hold(OutFig.Axes.dIA.Pure,'on')
plot(OutFig.Axes.dIA.Pure,Alpha,ydata,'LineWidth',1.5)
plot(OutFig.Axes.dIA.Pure,Alpha,yfit.dIA,'LineWidth',1.5)
grid(OutFig.Axes.dIA.Pure,'on')
title(OutFig.Axes.dIA.Pure,'dIA Fit')
legend(OutFig.Axes.dIA.Pure,'Spline','Pacejka','Location','best')


%% dIA and dFz parameters
ubIAFz = [ 10,  10];
lbIAFz = [-10, -10];

Fz_N  = Fz_vals.*4.448;

dIAFz_Fit.Kyg0    = @(XIFz) Fz_N.*(XIA(6)+(XIFz(1).*dfz));

dIAFz_Fit.SVyg    = @(XIFz) Fz_N.*(XIA(7)+XIFz(2).*dfz).*(gamma_star);

dIAFz_Fit.Ky_a    = @(XIFz) Xb(6).*Fz_0_prime.*(1-XIA(4).*abs(gamma_star)).*sin(Xb(8).*atan((Fz_N./Fz_0_prime)./(Xb(7)+(XIA(5).*(gamma_star.^2)))));

dIAFz_Fit.S_Hy    = @(XIFz) (Xb(5) + Xf(3).*dfz)+ ((dIAFz_Fit.Kyg0(XIFz).*gamma_star - dIAFz_Fit.SVyg(XIFz))./(dIAFz_Fit.Ky_a(XIFz)+epsilon.k));

dIAFz_Fit.mu_y    = @(XIFz) (Xb(2)+Xf(1).*dfz).*(1-XIA(1).*(gamma_star.^2));

dIAFz_Fit.Alpha_y = @(XIFz) Alpha_star + dIAFz_Fit.S_Hy(XIFz);

dIAFz_Fit.C_y     = @(XIFz) Xb(1);

dIAFz_Fit.D_y     = @(XIFz) dIAFz_Fit.mu_y(XIFz).*Fz_N;

dIAFz_Fit.E_y     = @(XIFz) (Xb(3)+Xf(2).*dfz).* (1 + XIA(3).*(gamma_star.^2) - (Xb(4)+XIA(2).*gamma_star).*sign(Alpha_star));

dIAFz_Fit.B_y     = @(XIFz) dIAFz_Fit.Ky_a(XIFz)./(dIAFz_Fit.C_y(XIFz).*dIAFz_Fit.D_y(XIFz) + epsilon.y);

dIAFz_Fit.S_Vy    = @(XIFz) Fz_N.*(Xb(9)+Xf(4).*dfz) + dIAFz_Fit.SVyg(XIFz);

dIAFz_Fit.F_yo    = @(XIFz,Alpha_star) dIAFz_Fit.D_y(XIFz).*sin(dIAFz_Fit.C_y(XIFz).*atan(dIAFz_Fit.B_y(XIFz).*dIAFz_Fit.Alpha_y(XIFz)-dIAFz_Fit.E_y(XIFz).*(dIAFz_Fit.B_y(XIFz).*dIAFz_Fit.Alpha_y(XIFz)-atan(dIAFz_Fit.B_y(XIFz).*dIAFz_Fit.Alpha_y(XIFz))))) + dIAFz_Fit.S_Vy(XIFz);

FyVar = strcat('FY_',TestID,'_',string(Fz_vals),'FZ_12P_',string(gamma_vals),'IA');
ydata = SplineData.P12.SA0.(strcat('IA',string(gamma_vals))).(FyVar);


XIFz= lsqcurvefit(dIAFz_Fit.F_yo,x0IAFz,Alpha_star,ydata,lbIAFz,ubIAFz,opts_base);
yfit.dIAFz =feval(dIAFz_Fit.F_yo,XIFz,Alpha_star);

for n = 1:length(XIFz)
    IAdFzList{n,4} = XIFz(n);
    IAdFzList{n,5} = lbIAFz(n);
    IAdFzList{n,6} = ubIAFz(n);
end
IAdFzList  = cell2table(IAdFzList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});

OutFig.Tabs.dIAFz.Pure= uitab(OutFig.TabGroup.Pure,'Title','dIAFz');
OutFig.Axes.dIAFz.Pure = axes(OutFig.Tabs.dIAFz.Pure);
hold(OutFig.Axes.dIAFz.Pure,'on')
plot(OutFig.Axes.dIAFz.Pure,Alpha,ydata,'LineWidth',1.5)
plot(OutFig.Axes.dIAFz.Pure,Alpha,yfit.dIAFz,'LineWidth',1.5)
grid(OutFig.Axes.dIAFz.Pure,'on')
title(OutFig.Axes.dIAFz.Pure,'dIAFz Fit')
legend(OutFig.Axes.dIAFz.Pure,'Spline','Pacejka','Location','best')


FY_ParameterList = [BaseList;FzList;dPiList;IAList;IAdFzList]; % maybe do this as a struct to house each normal load for each tire!!

% FY_ParameterList  = cell2table(FY_ParameterList,"VariableNames",{'Structure';'Variable';'Initial';'Final';'Lower';'Upper'});     
FileName = strcat('FY_Parameters','_',Tire,'_',string(Round),'_',string(Run),'_', string(Fz_nom), 'FZ','.mat');
save(strcat("CC's tire model folder\Fitted Parameters\",FileName),'FY_ParameterList')

end