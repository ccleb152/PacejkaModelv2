function [SplineData] = Raw_Data_Fitter_Fy_V2(Round,Run,Tire)
 
RnIdentifier = strcat('R',string(Round),'_','Rn',string(Run));
FilePrefix = strcat(RnIdentifier,'_', Tire);
SweepVars.Fz = string([50]');
SweepVars.IA = string([0]');
SweepVars.SA = string([0]);
SweepVars.P  = string([12]');
SweepVars.V  = string([25]');
RawDataVars = string(['MZ';'FX';'FY';'SA']);
 
z = 0;
for n = 1:length(SweepVars.Fz) % normal load
        for j = 1:length(SweepVars.SA) % slip angle
          for m = 1:length(SweepVars.IA) % inclination angle
            for k = 1:length(SweepVars.P) % pressure
                for q = 1:length(SweepVars.V) % velocity
                    z = z+1;
                    FZname = string(SweepVars.Fz(n));
                    Pname = string(SweepVars.P(k));
                    IAname = string(SweepVars.IA(m));
                    Vname = string(SweepVars.V(q));
                    SAname = string(SweepVars.SA(j));
                    
                    File = strcat(FilePrefix,'_',Pname,'psi','_',SAname,'SA','_',FZname,'FZ','_',IAname,'IA','_',Vname);
                    SA_Var = strcat('SA_',RnIdentifier,'_',FZname,'FZ_',Pname,'P_',IAname,'IA');
                    SL_Var =  strcat('SL_',RnIdentifier,'_',FZname,'FZ_',Pname,'P_',IAname,'IA');
                    FY_Var = strcat('FY_',RnIdentifier,'_',FZname,'FZ_',Pname,'P_',IAname,'IA');
                    FX_Var = strcat('FX_',RnIdentifier,'_',FZname,'FZ_',Pname,'P_',IAname,'IA');
                    MZ_Var = strcat('MZ_',RnIdentifier,'_',FZname,'FZ_',Pname,'P_',IAname,'IA');
                    
                    
                    V_Var = strcat('V_',RnIdentifier,'_',FZname,'FZ_',Pname,'P_',IAname,'IA');
                    Vc_Var = strcat('Vc_',RnIdentifier,'_',FZname,'FZ_',Pname,'P_',IAname,'IA');
                    StructName = strcat(RnIdentifier,'.P',Pname,'.FZ',FZname,'.IA',IAname);
                    %               eval(StructName) = struct();
                    File
                    load(strcat(File,'.mat'),SL_Var,SA_Var,FY_Var,FX_Var,MZ_Var,Vc_Var) % loading data
                    
                    
                    SA_data = eval(SA_Var); % extracts data into two variables
                    FY_data = eval(FY_Var);

                    % "FITS" fitting data to smoothing splines with
                    % different var's
                    
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsFx = fit(eval(SA_Var)',eval(FX_Var)','smoothingspline','SmoothingParam',0.99999);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsFy = fit(eval(SA_Var)',eval(FY_Var)','smoothingspline','SmoothingParam',0.90);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsMz = fit(eval(SA_Var)',eval(MZ_Var)','smoothingspline','SmoothingParam',0.1);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsVc = fit(eval(SA_Var)',eval(Vc_Var)','smoothingspline','SmoothingParam',0.99999);
                    
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).FX = eval(FX_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).FY = eval(FY_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SL = eval(SL_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SA = eval(SA_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).MZ = eval(MZ_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).RL = eval(MZ_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Vc = eval(Vc_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange = (-12.25:0.05:12.25)'; % fitted over specified slip angle range
                    
                    SA = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange;
                    FX = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsFx(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange);
                    FY = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsFy(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange);
                    MZ = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsMz(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange);
                    for b = 1:length(RawDataVars)
                        DesiredVars = char(strcat(RawDataVars{b,1},'_',RnIdentifier,'_',(SweepVars.Fz(n)),'FZ_',(SweepVars.P(k)),'P_',(SweepVars.IA(m)),'IA'));
                        DataVector = eval(RawDataVars{b,1});
                        SplineData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).(DesiredVars) = DataVector;
                    end
                    SplineData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).RawData.(strcat('FZ',FZname)).SA = SA_data;
                    SplineData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).RawData.(strcat('FZ',FZname)).FY = FY_data;
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Fx_Fit = FX;
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Fy_Fit = FY;
                  % Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).MZ_Fit = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsMz(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange);
                   % Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Vc_Fit = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsVc(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange);
                    
%                 figure(z)
%                 clf
%                 hold on
%                 plot(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SA ,Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).FY,...
%                     '.','LineWidth',1.5);
%                 
%                 plot(SA,FY,'LineWidth',1.5);
%                 grid on
%                 title(strcat(FZname,'FZ{ }',SAname,'SA{ }',IAname,'IA'))
%                
                end
            end
        end
    end
end
 end
% clearvars('n','m','p','q','FZname','Pname','IAname','Vname')