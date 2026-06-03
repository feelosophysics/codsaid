



- 운영/정리(필수)
  - 과금 방지를 위해 아래 리소스는 생성 시점부터 “정리 대상”으로 추적한다.
    - EC2(종료 상태 확인)
    - Elastic IP(Release 확인)
    - NAT Gateway(삭제 확인, 생성했다면)
    - ELB/ALB(삭제 확인, 생성했다면)
    - RDS(삭제 확인, 생성했다면)
    - EBS Volumes(미사용 볼륨 포함 삭제 확인)
  - 모든 리소스 삭제 후 Billing Dashboard 확인을 권장한다.



- 리소스 정리 체크리스트 예시
  - EC2 인스턴스 Terminated 확인
  - EBS 볼륨(미사용 포함) 삭제 확인
  - Elastic IP Release 확인(할당했다면)
  - Internet Gateway Detach 및 삭제 확인
  - VPC 및 Subnet/Route Table 삭제 확인
  - (해당 시) NAT Gateway 삭제 확인
  - (해당 시) ELB/ALB 삭제 확인
  - (해당 시) RDS 삭제 확인
  - (권장) 모든 리소스 삭제 후 Billing Dashboard에서 과금 항목이 남지 않는지 확인


