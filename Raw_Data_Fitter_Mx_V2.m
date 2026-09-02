 function [SplineData] = Raw_Data_Fitter_MX_V2(Round,Run,Tire)
 
RnIdentifier = strcat('R',string(Round),'_','Rn',string(Run));
FilePrefix = strcat(RnIdentifier,'_', Tire);
SweepVars.Fz = string([50 100 150 200 250]');
SweepVars.IA = string([0 2]');
SweepVars.SA = string([0]);
SweepVars.P  = string([12]');
SweepVars.V  = string([25]');
RawDataVars = string(['MX';'SA']);

 
z = 0;
for n = 1:length(SweepVars.Fz)
        for j = 1:length(SweepVars.SA)
          for m = 1:length(SweepVars.IA)
            for k = 1:length(SweepVars.P)
                for q = 1:length(SweepVars.V)
                    z = z+1;
                    SA_data = [];
                    MX_data = [];
                    FZname = string(SweepVars.Fz(n));
                    Pname = string(SweepVars.P(k));
                    IAname = string(SweepVars.IA(m));
                    Vname = string(SweepVars.V(q));
                    SAname = string(SweepVars.SA(j));
                    File = strcat(FilePrefix,'_',Pname,'psi','_',SAname,'SA','_',FZname,'FZ','_',IAname,'IA','_',Vname);
                    SA_Var = strcat('SA_',RnIdentifier,'_',FZname,'FZ_',Pname,'P_',IAname,'IA');
                    MX_Var = strcat('MX_',RnIdentifier,'_',FZname,'FZ_',Pname,'P_',IAname,'IA');
                    load(strcat(File,'.mat'),SA_Var,MX_Var)
                    
                    StructName = strcat(RnIdentifier,'.P',Pname,'.FZ',FZname,'.IA',IAname);
                    %               eval(StructName) = struct();
                    
                    SA_data = eval(SA_Var);
                    MX_data = eval(MX_Var);
                    Index = [find(SA_data == max(SA_data),1,'last') , find(SA_data == min(SA_data),1,'first')-1];
                    Max1 = max(SA_data(1:(Index(1))-1));
                    Min2 = min(SA_data((Index(2)+1):end));
                    MX_data([1:Index(1),Index(2):length(SA_data)]) = [];
                    SA_data([1:Index(1),Index(2):length(SA_data)]) = [];
                    
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsFx = fit(eval(SA_Var)',eval(FX_Var)','smoothingspline','SmoothingParam',0.99999);
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsFy = fit(eval(SA_Var)',eval(FY_Var)','smoothingspline','SmoothingParam',0.90);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsMz = fit(SA_data',MX_data','smoothingspline','SmoothingParam',0.9);
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsVc = fit(eval(SA_Var)',eval(Vc_Var)','smoothingspline','SmoothingParam',0.99999);
                    
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).FX = eval(FX_Var);
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).FY = eval(FY_Var);
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SL = eval(SL_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SA = SA_data;
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).MX = MX_data;
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).RL = eval(MX_Var);
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Vc = eval(Vc_Var);
                    Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange = [(-12.3:0.05:-4.7)'; (-4.675:0.025:4.675)'; (4.7:0.05:12.3)'];
                    
                    SA = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange;
%                     FX = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsFx(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange);
%                     FY = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsFy(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange);
                    MX = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SAvsMz(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SARange);
                    for b = 1:length(RawDataVars)
                        DesiredVars = char(strcat(RawDataVars{b,1},'_',RnIdentifier,'_',(SweepVars.Fz(n)),'FZ_',(SweepVars.P(k)),'P_',(SweepVars.IA(m)),'IA'));
                        DataVector = eval(RawDataVars{b,1});
                        SplineData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).(DesiredVars) = DataVector;
                        SplineData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).RawData.(strcat('FZ',FZname)).SA = SA_data;
                        SplineData.(strcat('P',SweepVars.P(k))).(strcat('SA',SweepVars.SA(j))).(strcat('IA',SweepVars.IA(m))).RawData.(strcat('FZ',FZname)).MX = MX_data;
                    end
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Fx_Fit = FX;
%                     Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).Fy_Fit = FY;
                  % Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).MX_Fit = Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLvsMz(Fits.(strcat('P',Pname)).(strcat('SA',SAname)).(strcat('IA',IAname)).(strcat('FZ',FZname)).SLRange);
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