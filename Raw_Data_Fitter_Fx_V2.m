function [SplineData] = Raw_Data_Fitter_Fx_V2(Round,Run,Tire)
RnIdentifier = strcat('R',string(Round),'_','Rn',string(Run));
FilePrefix = strcat(RnIdentifier,'_', Tire);
SweepVars.Fz = string([50 150 200 250]');
SweepVars.IA = string([0 2]');
SweepVars.SA = string([0]);
SweepVars.P  = string([12]');
SweepVars.V  = string([25]');
RawDataVars = string(['FX';'FY';'Mz';'SL']);

 
z = 0;
for n = 1:length(SweepVars.Fz)
        for j = 1:length(SweepVars.SA)
          for m = 1:length(SweepVars.IA)
            for k = 1:length(SweepVars.P)
                for q = 1:length(SweepVars.V)
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
                    load(strcat(File,'.mat'),SL_Var,SA_Var,FY_Var,FX_Var,MZ_Var,Vc_Var)
                    SL_data = eval(SL_Var);
                    FX_data = eval(FX_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsFx = fit(eval(SL_Var)',eval(FX_Var)','smoothingspline','SmoothingParam',0.99999999);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsFy = fit(eval(SL_Var)',eval(FY_Var)','smoothingspline','SmoothingParam',0.9999999);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsMz = fit(eval(SL_Var)',eval(MZ_Var)','smoothingspline','SmoothingParam',0.99999);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsVc = fit(eval(SL_Var)',eval(Vc_Var)','smoothingspline','SmoothingParam',0.99999);
                    
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).FX = eval(FX_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).FY = eval(FY_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SL = eval(SL_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SA = eval(SA_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).MZ = eval(MZ_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).RL = eval(MZ_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Vc = eval(Vc_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange = (-0.161:0.001:0.141)';
                    
                    SL = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange;
                    FX = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsFx(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange);
                    FY = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsFy(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange);
                    Mz = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsMz(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange);
                    for b = 1:length(RawDataVars)
                        DesiredVars = char(strcat(RawDataVars{b,1},'_',RnIdentifier,'_',(SweepVars.Fz(n)),'FZ_',(SweepVars.P(k)),'P_',(SweepVars.IA(m)),'IA'));
                        DataVector = eval(RawDataVars{b,1});
                        SplineData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).(DesiredVars) = DataVector;
                    end
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Fx_Fit = FX;
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Fy_Fit = FY;
                    SplineData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).RawData.(strcat('FZ',FZname)).SL = SL_data;
                    SplineData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).RawData.(strcat('FZ',FZname)).FX = FX_data;
                  % Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).MZ_Fit = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsMz(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange);
                   % Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Vc_Fit = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsVc(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange);
                    
%                 figure(z)
%                 clf
%                 hold on
%                 plot(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SL ,Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).FY,...
%                     '.','LineWidth',1.5);
%                 
%                 plot(SL,FY,'LineWidth',1.5);
%                 grid on
%                 title(strcat(FZname,'FZ{ }',SAname,'SA{ }',IAname,'IA'))
%                
                end
            end
        end
    end
end
 
% clearvars('n','m','p','q','FZname','Pname','IAname','Vname')